"""Embedding pipeline using BGE + ChromaDB with precomputed embedding cache."""
import hashlib
import logging
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
from config.settings import settings
from backend.models.schemas import CodeChunk

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self):
        self._model = None
        self._client = None
        self._collection = None

    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer(
                settings.embedding_model,
                device=settings.embedding_device,
            )
        return self._model

    @property
    def client(self):
        if self._client is None:
            persist_dir = Path(settings.chroma_persist_dir)
            persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(persist_dir))
        return self._client

    def get_collection(self, name: str = None):
        col_name = name or settings.chroma_collection
        return self.client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def compute_content_hash(chunks: list[CodeChunk]) -> str:
        """Compute a stable hash of all chunk content for cache invalidation."""
        h = hashlib.sha256()
        for c in sorted(chunks, key=lambda x: x.chunk_id):
            h.update(c.chunk_id.encode())
            h.update(c.content.encode())
        return h.hexdigest()[:16]

    def has_cached_embeddings(self, collection_name: str, content_hash: str) -> bool:
        """Check if embeddings already exist for this content hash."""
        try:
            col = self.client.get_collection(collection_name)
            meta = col.metadata or {}
            if meta.get("content_hash") == content_hash and col.count() > 0:
                logger.info(f"Embedding cache hit for {collection_name} (hash={content_hash})")
                return True
        except Exception:
            pass
        return False

    def embed_chunks(self, chunks: list[CodeChunk], collection_name: str = None,
                     content_hash: str = None):
        """Embed chunks into ChromaDB. Skips if content_hash matches cached version."""
        col_name = collection_name or settings.chroma_collection

        # Check cache — skip if embeddings already exist for this hash
        if content_hash and self.has_cached_embeddings(col_name, content_hash):
            return

        # Delete old collection and recreate with new hash metadata
        self.delete_collection(col_name)
        meta = {"hnsw:space": "cosine"}
        if content_hash:
            meta["content_hash"] = content_hash
        collection = self.client.get_or_create_collection(name=col_name, metadata=meta)

        batch_size = 64
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c.content for c in batch]
            ids = [c.chunk_id for c in batch]
            metadatas = [
                {
                    "file_path": c.file_path,
                    "chunk_type": c.chunk_type,
                    "language": c.language,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                }
                for c in batch
            ]

            embeddings = self.model.encode(texts, show_progress_bar=False).tolist()
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

        logger.info(f"Embedded {len(chunks)} chunks into {col_name} (hash={content_hash})")

    def query(self, query_text: str, n_results: int = 5, collection_name: str = None) -> list[dict]:
        collection = self.get_collection(collection_name)
        query_embedding = self.model.encode([query_text]).tolist()

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        output = []
        if results["documents"]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                output.append({
                    "content": doc,
                    "metadata": meta,
                    "distance": dist,
                })
        return output

    def delete_collection(self, name: str = None):
        col_name = name or settings.chroma_collection
        try:
            self.client.delete_collection(col_name)
        except Exception:
            pass


vector_store = VectorStore()
