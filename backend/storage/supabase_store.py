"""Supabase storage backend — vectors, job tracking, and results.

Replaces ChromaDB when configured. Uses pgvector for embeddings
and regular tables for job state + analysis results.

Required Supabase setup (run once via SQL editor):

    -- Enable vector extension
    create extension if not exists vector;

    -- Embeddings table
    create table code_chunks (
        id text primary key,
        collection text not null,
        content text not null,
        embedding vector(384),  -- BGE-small dimension
        file_path text,
        chunk_type text,
        language text,
        start_line int,
        end_line int,
        content_hash text,
        created_at timestamptz default now()
    );

    -- Similarity search function
    create or replace function match_chunks(
        query_embedding vector(384),
        match_collection text,
        match_count int default 5
    ) returns table (
        id text,
        content text,
        file_path text,
        chunk_type text,
        language text,
        start_line int,
        end_line int,
        similarity float
    ) language plpgsql as $$
    begin
        return query
        select
            c.id, c.content, c.file_path, c.chunk_type,
            c.language, c.start_line, c.end_line,
            1 - (c.embedding <=> query_embedding) as similarity
        from code_chunks c
        where c.collection = match_collection
        order by c.embedding <=> query_embedding
        limit match_count;
    end;
    $$;

    -- Jobs table
    create table analysis_jobs (
        job_id text primary key,
        repo_url text not null,
        branch text default 'main',
        status text default 'pending',
        result jsonb,
        agent_events jsonb default '[]'::jsonb,
        created_at timestamptz default now(),
        completed_at timestamptz
    );

    -- Index for fast collection queries
    create index idx_chunks_collection on code_chunks(collection);
    create index idx_jobs_repo on analysis_jobs(repo_url);
"""
import json
import logging
from typing import Optional
from config.settings import settings

logger = logging.getLogger(__name__)

# Lazy import — supabase may not be installed
_supabase_client = None


def _get_client():
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client
            _supabase_client = create_client(
                settings.supabase_url,
                settings.supabase_service_key,
            )
            logger.info("Supabase client initialized")
        except ImportError:
            raise ImportError("Install supabase: pip install supabase")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Supabase: {e}")
    return _supabase_client


class SupabaseStore:
    """Supabase-backed storage for vectors, jobs, and results."""

    def __init__(self):
        self._embedding_model = None

    @property
    def client(self):
        return _get_client()

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer(
                settings.embedding_model,
                device=settings.embedding_device,
            )
        return self._embedding_model

    def is_configured(self) -> bool:
        return bool(settings.supabase_url and settings.supabase_service_key)

    # ====== Vector Operations ======

    def embed_chunks(self, chunks, collection_name: str, content_hash: str = None):
        """Embed and store code chunks in Supabase pgvector."""
        # Check if already embedded
        if content_hash:
            existing = self.client.table("code_chunks").select("id").eq(
                "collection", collection_name
            ).eq("content_hash", content_hash).limit(1).execute()
            if existing.data:
                logger.info(f"Supabase embedding cache hit for {collection_name}")
                return

        # Delete old chunks for this collection
        self.client.table("code_chunks").delete().eq("collection", collection_name).execute()

        # Embed in batches
        batch_size = 64
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c.content for c in batch]
            embeddings = self.embedding_model.encode(texts, show_progress_bar=False).tolist()

            rows = []
            for c, emb in zip(batch, embeddings):
                rows.append({
                    "id": c.chunk_id,
                    "collection": collection_name,
                    "content": c.content,
                    "embedding": emb,
                    "file_path": c.file_path,
                    "chunk_type": c.chunk_type,
                    "language": c.language,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "content_hash": content_hash,
                })

            self.client.table("code_chunks").upsert(rows).execute()

        logger.info(f"Embedded {len(chunks)} chunks to Supabase ({collection_name})")

    def query(self, query_text: str, n_results: int = 5, collection_name: str = None) -> list[dict]:
        """Vector similarity search via pgvector."""
        query_embedding = self.embedding_model.encode([query_text]).tolist()[0]

        result = self.client.rpc("match_chunks", {
            "query_embedding": query_embedding,
            "match_collection": collection_name or settings.chroma_collection,
            "match_count": n_results,
        }).execute()

        output = []
        for row in result.data or []:
            output.append({
                "content": row["content"],
                "metadata": {
                    "file_path": row["file_path"],
                    "chunk_type": row["chunk_type"],
                    "language": row["language"],
                    "start_line": row["start_line"],
                    "end_line": row["end_line"],
                },
                "distance": 1 - row["similarity"],
            })
        return output

    # ====== Job Tracking ======

    def create_job(self, job_id: str, repo_url: str, branch: str = "main"):
        """Create a new analysis job."""
        self.client.table("analysis_jobs").insert({
            "job_id": job_id,
            "repo_url": repo_url,
            "branch": branch,
            "status": "pending",
        }).execute()

    def update_job_status(self, job_id: str, status: str):
        """Update job status."""
        update = {"status": status}
        if status == "completed":
            from datetime import datetime, timezone
            update["completed_at"] = datetime.now(timezone.utc).isoformat()
        self.client.table("analysis_jobs").update(update).eq("job_id", job_id).execute()

    def store_result(self, job_id: str, result: dict):
        """Store analysis result."""
        self.client.table("analysis_jobs").update({
            "result": json.dumps(result, default=str),
            "status": "completed",
        }).eq("job_id", job_id).execute()

    def get_result(self, job_id: str) -> Optional[dict]:
        """Get analysis result by job ID."""
        row = self.client.table("analysis_jobs").select("*").eq(
            "job_id", job_id
        ).single().execute()
        if row.data and row.data.get("result"):
            return json.loads(row.data["result"]) if isinstance(row.data["result"], str) else row.data["result"]
        return None

    def append_events(self, job_id: str, events: list[dict]):
        """Append agent events to job."""
        # Get existing events
        row = self.client.table("analysis_jobs").select("agent_events").eq(
            "job_id", job_id
        ).single().execute()
        existing = row.data.get("agent_events", []) if row.data else []
        if isinstance(existing, str):
            existing = json.loads(existing)
        existing.extend(events)
        self.client.table("analysis_jobs").update({
            "agent_events": json.dumps(existing, default=str),
        }).eq("job_id", job_id).execute()

    def delete_collection(self, collection_name: str):
        """Delete all chunks for a collection."""
        self.client.table("code_chunks").delete().eq("collection", collection_name).execute()


# Singleton
supabase_store = SupabaseStore()
