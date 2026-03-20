"""Utility helpers."""
import hashlib
import json
import os
from pathlib import Path
from config.settings import settings


LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".tsx": "tsx", ".jsx": "jsx", ".java": "java", ".go": "go",
    ".rs": "rust", ".cpp": "cpp", ".c": "c", ".h": "c",
    ".rb": "ruby", ".php": "php", ".cs": "csharp",
    ".swift": "swift", ".kt": "kotlin",
}


def detect_language(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return LANG_MAP.get(ext, "unknown")


def chunk_id(file_path: str, start_line: int, chunk_type: str) -> str:
    raw = f"{file_path}:{start_line}:{chunk_type}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def stable_repo_hash(repo_url: str) -> str:
    """Stable hash for repo URL — safe across process restarts."""
    return hashlib.md5(repo_url.encode()).hexdigest()[:12]


def collection_name_for(repo_url: str) -> str:
    """Deterministic ChromaDB collection name for a repo."""
    return f"repo_{stable_repo_hash(repo_url)}"


def read_file_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def truncate(text: str, max_chars: int = 4000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


class CacheManager:
    def __init__(self):
        self.cache_dir = Path(settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, namespace: str, identifier: str) -> str:
        raw = f"{namespace}:{identifier}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, namespace: str, identifier: str) -> dict | None:
        if not settings.enable_cache:
            return None
        path = self.cache_dir / f"{self._key(namespace, identifier)}.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                return None
        return None

    def get_with_ttl(self, namespace: str, identifier: str, ttl: int) -> dict | None:
        """Get cached data only if it was written within ttl seconds."""
        if not settings.enable_cache:
            return None
        path = self.cache_dir / f"{self._key(namespace, identifier)}.json"
        if path.exists():
            try:
                import time
                age = time.time() - path.stat().st_mtime
                if age > ttl:
                    return None
                return json.loads(path.read_text())
            except Exception:
                return None
        return None

    def set(self, namespace: str, identifier: str, data: dict):
        if not settings.enable_cache:
            return
        path = self.cache_dir / f"{self._key(namespace, identifier)}.json"
        path.write_text(json.dumps(data, indent=2))

    def clear(self, namespace: str = None):
        if namespace:
            for f in self.cache_dir.glob("*.json"):
                f.unlink()
        else:
            for f in self.cache_dir.glob("*.json"):
                f.unlink()


cache = CacheManager()
