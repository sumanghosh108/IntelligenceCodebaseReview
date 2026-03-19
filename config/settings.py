"""Application configuration settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_timeout: int = 120

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

    class Config:
        env_file = ".env"
        env_prefix = "ICR_"


settings = Settings()
