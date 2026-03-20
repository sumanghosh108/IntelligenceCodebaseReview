"""Application configuration settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_timeout: int = 300  # 5 min — allows for CoT (3 LLM calls) and large prompts
    ollama_num_ctx: int = 8192  # Context window size for Ollama models

    # Hybrid Model Strategy — task-specialized models
    # Defaults to llama3 for all. Install & configure specialized models for better results:
    #   ICR_MODEL_FAST=phi3            (fast summarization, tech stack, cost)
    #   ICR_MODEL_CODE=deepseek-coder  (code reasoning, file/function analysis, security)
    #   ICR_MODEL_DEEP=llama3          (synthesis, recommendations, interview)
    model_fast: str = "llama3"
    model_code: str = "llama3"
    model_deep: str = "llama3"

    # Embeddings
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_device: str = "cpu"

    # ChromaDB
    chroma_persist_dir: str = "./data/chromadb"
    chroma_collection: str = "codebase_chunks"

    # Parsing
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
    llm_concurrency: int = 2  # Ollama queues requests; 2 avoids timeout cascading
    parse_workers: int = 8

    # Result cache TTL (seconds) — skip re-analysis if last result is within this window
    result_cache_ttl: int = 3600  # 1 hour

    # Chain-of-Thought — use multi-step reasoning for deep analysis tasks
    cot_enabled: bool = True
    # Which tasks get CoT (deep tasks only, fast tasks skip it)
    cot_tasks: str = "overview,system_flow,security,production,synthesis,recommendations"

    class Config:
        env_file = ".env"
        env_prefix = "ICR_"


settings = Settings()
