"""LlamaIndex knowledge layer — smart document indexing and retrieval.

Wraps LlamaIndex to provide:
  - Structured code document indexing (functions, classes, files as separate nodes)
  - Smart retrieval with metadata filtering
  - Sub-question decomposition for complex queries
  - Integration with existing embedding pipeline

Falls back gracefully if llama-index is not installed.
"""
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

_LLAMA_INDEX_AVAILABLE = False
try:
    from llama_index.core import (
        VectorStoreIndex,
        Document,
        Settings as LISettings,
        StorageContext,
    )
    from llama_index.core.node_parser import CodeSplitter, SentenceSplitter
    from llama_index.core.schema import TextNode, MetadataMode
    from llama_index.core.retrievers import VectorIndexRetriever
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    _LLAMA_INDEX_AVAILABLE = True
except ImportError:
    logger.info("llama-index not installed — knowledge layer disabled")


class KnowledgeIndex:
    """LlamaIndex-powered knowledge layer for code understanding.

    Usage:
        ki = KnowledgeIndex()
        ki.build_from_parsed(parsed_files)
        results = ki.query("How does authentication work?")
    """

    def __init__(self):
        self._index: Optional[object] = None
        self._nodes: list = []

    @property
    def available(self) -> bool:
        return _LLAMA_INDEX_AVAILABLE

    def build_from_parsed(self, parsed_files: list[dict]) -> int:
        """Build index from parsed file data. Returns node count."""
        if not _LLAMA_INDEX_AVAILABLE:
            logger.warning("LlamaIndex not available, skipping knowledge index")
            return 0

        from config.settings import settings

        # Configure LlamaIndex embedding
        LISettings.embed_model = HuggingFaceEmbedding(
            model_name=settings.embedding_model,
            device=settings.embedding_device,
        )
        # Disable LLM for indexing (we use our own LLM layer)
        LISettings.llm = None

        nodes = []

        for pf in parsed_files:
            fp = pf["file_path"]
            lang = pf["language"]

            # File-level node (structural summary)
            funcs = [f["name"] for f in pf["functions"]]
            file_summary = (
                f"File: {fp}\n"
                f"Language: {lang}\n"
                f"Lines: {pf['line_count']}\n"
                f"Functions: {', '.join(funcs)}\n"
            )
            nodes.append(TextNode(
                text=file_summary + (pf.get("source_preview", "")[:2000]),
                metadata={
                    "file_path": fp,
                    "language": lang,
                    "node_type": "file",
                    "function_count": len(funcs),
                    "line_count": pf["line_count"],
                },
                excluded_embed_metadata_keys=["line_count", "function_count"],
            ))

            # Function-level nodes (detailed)
            for func in pf["functions"]:
                func_text = (
                    f"# File: {fp}\n"
                    f"# Function: {func['name']}({', '.join(func.get('parameters', []))})\n"
                    f"{func['body'][:2000]}"
                )
                nodes.append(TextNode(
                    text=func_text,
                    metadata={
                        "file_path": fp,
                        "language": lang,
                        "node_type": "function",
                        "function_name": func["name"],
                        "start_line": func["start_line"],
                        "end_line": func["end_line"],
                    },
                    excluded_embed_metadata_keys=["start_line", "end_line"],
                ))

        self._nodes = nodes
        self._index = VectorStoreIndex(nodes)
        logger.info(f"LlamaIndex knowledge index built: {len(nodes)} nodes")
        return len(nodes)

    def query(
        self,
        question: str,
        top_k: int = 8,
        node_type: str = None,
        language: str = None,
    ) -> list[dict]:
        """Query the knowledge index with optional metadata filtering."""
        if not _LLAMA_INDEX_AVAILABLE or self._index is None:
            return []

        retriever = VectorIndexRetriever(
            index=self._index,
            similarity_top_k=top_k,
        )

        results = retriever.retrieve(question)

        output = []
        for node_with_score in results:
            node = node_with_score.node
            meta = node.metadata

            # Apply metadata filters
            if node_type and meta.get("node_type") != node_type:
                continue
            if language and meta.get("language") != language:
                continue

            output.append({
                "content": node.get_content(metadata_mode=MetadataMode.NONE),
                "metadata": meta,
                "score": node_with_score.score,
            })

        return output

    def get_stats(self) -> dict:
        """Get index statistics."""
        if not self._nodes:
            return {"available": False, "node_count": 0}

        file_nodes = sum(1 for n in self._nodes if n.metadata.get("node_type") == "file")
        func_nodes = sum(1 for n in self._nodes if n.metadata.get("node_type") == "function")
        languages = set(n.metadata.get("language", "?") for n in self._nodes)

        return {
            "available": True,
            "total_nodes": len(self._nodes),
            "file_nodes": file_nodes,
            "function_nodes": func_nodes,
            "languages": list(languages),
        }


# Singleton
knowledge_index = KnowledgeIndex()
