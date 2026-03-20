"""Hybrid search engine — BM25 keyword search + vector similarity + re-ranking.

Combines:
  1. BM25 (keyword/lexical) — exact term matching, great for identifiers & error messages
  2. Vector (semantic) — meaning-based matching, great for natural language questions
  3. Re-ranking — reciprocal rank fusion to merge results from both sources
  4. Metadata filtering — filter by chunk_type, language, file path patterns

This replaces basic similarity-only search for significantly better retrieval.
"""
import re
import math
import logging
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


class BM25Index:
    """BM25 (Okapi BM25) keyword search index.

    Built in-memory from embedded chunks. Lightweight alternative to rank-bm25
    with no extra dependencies.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: list[dict] = []       # [{id, content, metadata}]
        self.doc_freqs: dict[str, int] = defaultdict(int)  # term → doc count
        self.doc_lens: list[int] = []
        self.avg_dl: float = 0
        self.n_docs: int = 0
        self._term_freqs: list[dict[str, int]] = []  # per-doc term frequencies
        self._built = False

    def build(self, chunks: list[dict]):
        """Build the BM25 index from a list of chunks.

        Each chunk: {"id": str, "content": str, "metadata": dict}
        """
        self.docs = chunks
        self.n_docs = len(chunks)
        self.doc_freqs = defaultdict(int)
        self.doc_lens = []
        self._term_freqs = []

        for doc in chunks:
            tokens = self._tokenize(doc["content"])
            self.doc_lens.append(len(tokens))

            tf = defaultdict(int)
            seen_terms = set()
            for token in tokens:
                tf[token] += 1
                if token not in seen_terms:
                    self.doc_freqs[token] += 1
                    seen_terms.add(token)
            self._term_freqs.append(dict(tf))

        self.avg_dl = sum(self.doc_lens) / max(1, self.n_docs)
        self._built = True
        logger.info(f"BM25 index built: {self.n_docs} docs, {len(self.doc_freqs)} terms")

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """Search the index and return top-k results with BM25 scores."""
        if not self._built or self.n_docs == 0:
            return []

        query_tokens = self._tokenize(query)
        scores = []

        for i in range(self.n_docs):
            score = 0.0
            dl = self.doc_lens[i]
            tf_doc = self._term_freqs[i]

            for token in query_tokens:
                if token not in tf_doc:
                    continue
                tf = tf_doc[token]
                df = self.doc_freqs.get(token, 0)
                # IDF with smoothing
                idf = math.log((self.n_docs - df + 0.5) / (df + 0.5) + 1)
                # BM25 term score
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avg_dl)
                score += idf * numerator / denominator

            if score > 0:
                scores.append((i, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scores[:top_k]:
            doc = self.docs[idx]
            results.append({
                "id": doc["id"],
                "content": doc["content"],
                "metadata": doc["metadata"],
                "bm25_score": round(score, 4),
            })
        return results

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text for BM25: lowercase, split on non-alphanumeric,
        also split camelCase and snake_case into sub-tokens."""
        # Lowercase
        text = text.lower()
        # Split camelCase: insertSpace before uppercase
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        # Split snake_case
        text = text.replace('_', ' ')
        # Split on non-alphanumeric
        tokens = re.findall(r'[a-z0-9]+', text)
        # Remove very short tokens (1 char) and very common ones
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'in', 'on', 'at', 'to',
            'for', 'of', 'and', 'or', 'not', 'it', 'if', 'as', 'be', 'by',
            'this', 'that', 'with', 'from', 'but', 'has', 'had', 'have',
            'do', 'does', 'did', 'will', 'can', 'may', 'no', 'so', 'up',
            'def', 'return', 'self', 'none', 'true', 'false', 'import',
        }
        return [t for t in tokens if len(t) > 1 and t not in stop_words]


class HybridSearchEngine:
    """Combines BM25 + vector search with reciprocal rank fusion."""

    def __init__(self, vector_store, collection_name: str):
        self.vs = vector_store
        self.collection_name = collection_name
        self.bm25 = BM25Index()
        self._built = False

    def build_index(self, chunks: list[dict] = None):
        """Build BM25 index from chunks or from existing ChromaDB collection."""
        if chunks:
            bm25_docs = [
                {"id": c.chunk_id if hasattr(c, 'chunk_id') else c.get("id", str(i)),
                 "content": c.content if hasattr(c, 'content') else c.get("content", ""),
                 "metadata": {
                     "file_path": c.file_path if hasattr(c, 'file_path') else c.get("file_path", ""),
                     "chunk_type": c.chunk_type if hasattr(c, 'chunk_type') else c.get("chunk_type", ""),
                     "language": c.language if hasattr(c, 'language') else c.get("language", ""),
                     "start_line": c.start_line if hasattr(c, 'start_line') else c.get("start_line", 0),
                     "end_line": c.end_line if hasattr(c, 'end_line') else c.get("end_line", 0),
                 }}
                for i, c in enumerate(chunks)
            ]
        else:
            # Build from ChromaDB collection
            try:
                col = self.vs.get_collection(self.collection_name)
                all_data = col.get(include=["documents", "metadatas"])
                if not all_data["ids"]:
                    logger.warning(f"Collection {self.collection_name} is empty")
                    return
                bm25_docs = [
                    {"id": id_, "content": doc, "metadata": meta}
                    for id_, doc, meta in zip(
                        all_data["ids"], all_data["documents"], all_data["metadatas"]
                    )
                ]
            except Exception as e:
                logger.warning(f"Failed to build BM25 from collection: {e}")
                return

        self.bm25.build(bm25_docs)
        self._built = True

    def search(
        self,
        query: str,
        n_results: int = 8,
        chunk_type: Optional[str] = None,
        language: Optional[str] = None,
        file_pattern: Optional[str] = None,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ) -> list[dict]:
        """Hybrid search with reciprocal rank fusion.

        Args:
            query: Natural language or keyword query
            n_results: Number of results to return
            chunk_type: Filter by chunk type ("function", "class", "file")
            language: Filter by language
            file_pattern: Filter by file path substring
            vector_weight: Weight for vector similarity results (default 0.6)
            bm25_weight: Weight for BM25 keyword results (default 0.4)
        """
        # Detect if query looks like code/identifier (more keywords) vs natural language
        is_keyword_heavy = self._is_keyword_query(query)
        if is_keyword_heavy:
            vector_weight = 0.3
            bm25_weight = 0.7

        # 1. Vector search
        vector_results = self.vs.query(
            query, n_results=n_results * 2, collection_name=self.collection_name
        )

        # 2. BM25 search
        bm25_results = []
        if self._built:
            bm25_results = self.bm25.search(query, top_k=n_results * 2)

        # 3. Apply metadata filters
        if chunk_type or language or file_pattern:
            vector_results = self._filter(vector_results, chunk_type, language, file_pattern)
            bm25_results = self._filter_bm25(bm25_results, chunk_type, language, file_pattern)

        # 4. Reciprocal Rank Fusion
        fused = self._reciprocal_rank_fusion(
            vector_results, bm25_results,
            vector_weight=vector_weight, bm25_weight=bm25_weight,
        )

        # 5. Return top results
        return fused[:n_results]

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[dict],
        bm25_results: list[dict],
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
        k: int = 60,
    ) -> list[dict]:
        """Merge results using Reciprocal Rank Fusion (RRF).

        RRF score = sum(weight / (k + rank)) for each source.
        k=60 is standard, prevents high-ranked items from dominating.
        """
        scores: dict[str, float] = {}
        result_data: dict[str, dict] = {}

        # Score vector results
        for rank, r in enumerate(vector_results):
            # Use file_path + start_line as dedup key
            meta = r.get("metadata", {})
            key = f"{meta.get('file_path', '')}:{meta.get('start_line', 0)}"
            rrf_score = vector_weight / (k + rank + 1)
            scores[key] = scores.get(key, 0) + rrf_score
            if key not in result_data:
                result_data[key] = {
                    "content": r.get("content", ""),
                    "metadata": meta,
                    "vector_rank": rank + 1,
                    "vector_distance": r.get("distance", 1.0),
                }

        # Score BM25 results
        for rank, r in enumerate(bm25_results):
            meta = r.get("metadata", {})
            key = f"{meta.get('file_path', '')}:{meta.get('start_line', 0)}"
            rrf_score = bm25_weight / (k + rank + 1)
            scores[key] = scores.get(key, 0) + rrf_score
            if key not in result_data:
                result_data[key] = {
                    "content": r.get("content", ""),
                    "metadata": meta,
                }
            result_data[key]["bm25_rank"] = rank + 1
            result_data[key]["bm25_score"] = r.get("bm25_score", 0)

        # Sort by fused score
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)

        results = []
        for key in sorted_keys:
            data = result_data[key]
            data["rrf_score"] = round(scores[key], 6)
            data["sources"] = []
            if "vector_rank" in data:
                data["sources"].append("vector")
            if "bm25_rank" in data:
                data["sources"].append("bm25")
            results.append(data)

        return results

    @staticmethod
    def _is_keyword_query(query: str) -> bool:
        """Detect if query is keyword-heavy (code identifiers, error messages)
        vs natural language (questions, descriptions)."""
        # Indicators of natural language
        nl_indicators = ["how", "what", "why", "where", "when", "does", "explain", "describe", "tell"]
        query_lower = query.lower()
        if any(query_lower.startswith(w) or f" {w} " in f" {query_lower} " for w in nl_indicators):
            return False
        # Indicators of keyword/code query
        if re.search(r'[A-Z]{2}|_[a-z]|[a-z][A-Z]|\.\w+\(|::', query):
            return True
        # Short queries with few words are likely keywords
        if len(query.split()) <= 3:
            return True
        return False

    @staticmethod
    def _filter(results: list[dict], chunk_type: str = None,
                language: str = None, file_pattern: str = None) -> list[dict]:
        """Filter vector search results by metadata."""
        filtered = []
        for r in results:
            meta = r.get("metadata", {})
            if chunk_type and meta.get("chunk_type") != chunk_type:
                continue
            if language and meta.get("language") != language:
                continue
            if file_pattern and file_pattern.lower() not in meta.get("file_path", "").lower():
                continue
            filtered.append(r)
        return filtered

    @staticmethod
    def _filter_bm25(results: list[dict], chunk_type: str = None,
                     language: str = None, file_pattern: str = None) -> list[dict]:
        """Filter BM25 results by metadata."""
        filtered = []
        for r in results:
            meta = r.get("metadata", {})
            if chunk_type and meta.get("chunk_type") != chunk_type:
                continue
            if language and meta.get("language") != language:
                continue
            if file_pattern and file_pattern.lower() not in meta.get("file_path", "").lower():
                continue
            filtered.append(r)
        return filtered
