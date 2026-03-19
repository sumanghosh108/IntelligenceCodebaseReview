"""Embedding pipeline using BGE + ChromaDB."""
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
from config.settings import settings
from backend.models.schemas import CodeChunk


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

    def embed_chunks(self, chunks: list[CodeChunk], collection_name: str = None):
        collection = self.get_collection(collection_name)

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
