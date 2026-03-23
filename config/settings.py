"""Application configuration settings."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ====== LLM — OpenRouter ======
    openrouter_api_key: str = ""

    # ====== Multi-Agent System ======
    multi_agent_enabled: bool = True
    agent_concurrency: int = 4
    agent_max_retries: int = 2
    agent_task_timeout: int = 300

    # ====== Storage ======
    supabase_url: str = ""
    supabase_service_key: str = ""
    storage_backend: str = "chromadb"  # "chromadb" or "supabase"

    # ====== Embeddings ======
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_device: str = "cpu"

    # ChromaDB
    chroma_persist_dir: str = "./data/chromadb"
    chroma_collection: str = "codebase_chunks"

    # ====== Parsing ======
    max_file_size_kb: int = 500
    max_files_per_repo: int = 1000
    supported_extensions: str = ".py,.js,.ts,.tsx,.jsx,.java,.go,.rs,.cpp,.c,.h,.rb,.php,.cs,.swift,.kt"

    # Repo
    clone_dir: str = "./data/repos"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Cache
    cache_dir: str = "./data/cache"
    enable_cache: bool = True

    # Parallelism
    llm_concurrency: int = 4
    parse_workers: int = 8

    # Result cache TTL (seconds)
    result_cache_ttl: int = 3600

    # Chain-of-Thought
    cot_enabled: bool = True
    cot_tasks: str = "overview,system_flow,security,production,synthesis,recommendations"

    class Config:
        env_file = ".env"
        env_prefix = "ICR_"


settings = Settings()
