"""Repository cloning and management."""
import os
import shutil
import hashlib
from pathlib import Path
from git import Repo
from config.settings import settings


class RepoManager:
    def __init__(self):
        self.clone_dir = Path(settings.clone_dir)
        self.clone_dir.mkdir(parents=True, exist_ok=True)

    def _repo_hash(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def clone(self, repo_url: str, branch: str = "main") -> Path:
        repo_id = self._repo_hash(repo_url)
        target = self.clone_dir / repo_id

        if target.exists():
            shutil.rmtree(target)

        Repo.clone_from(repo_url, str(target), branch=branch, depth=1)
        return target

    def get_repo_path(self, repo_url: str) -> Path:
        repo_id = self._repo_hash(repo_url)
        return self.clone_dir / repo_id

    def list_files(self, repo_path: Path) -> list[Path]:
        extensions = set(settings.supported_extensions.split(","))
        max_size = settings.max_file_size_kb * 1024
        files = []
        count = 0

        for f in sorted(repo_path.rglob("*")):
            if count >= settings.max_files_per_repo:
                break
            if not f.is_file():
                continue
            if f.suffix not in extensions:
                continue
            # Skip hidden dirs, node_modules, venvs, etc.
            parts = f.relative_to(repo_path).parts
            skip_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__",
                         "dist", "build", ".next", ".cache", "vendor", "target"}
            if any(p in skip_dirs for p in parts):
                continue
            if f.stat().st_size > max_size:
                continue
            files.append(f)
            count += 1

        return files

    def get_folder_structure(self, repo_path: Path) -> dict:
        structure = {}
        for f in self.list_files(repo_path):
            rel = f.relative_to(repo_path)
            parts = rel.parts
            current = structure
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = None
        return structure

    def get_config_files(self, repo_path: Path) -> dict[str, str]:
        config_names = [
            "requirements.txt", "setup.py", "setup.cfg", "pyproject.toml",
            "package.json", "tsconfig.json", "Cargo.toml", "go.mod",
            "pom.xml", "build.gradle", "Gemfile", "composer.json",
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
            ".github/workflows", "Makefile", "CMakeLists.txt",
            "README.md", "README.rst", "README",
        ]
        result = {}
        for name in config_names:
            p = repo_path / name
            if p.is_file():
                try:
                    result[name] = p.read_text(encoding="utf-8", errors="replace")[:5000]
                except Exception:
                    pass
            elif p.is_dir():
                # Handle workflow dirs
                for wf in p.rglob("*.yml"):
                    key = str(wf.relative_to(repo_path))
                    try:
                        result[key] = wf.read_text(encoding="utf-8", errors="replace")[:3000]
                    except Exception:
                        pass
        return result

    def cleanup(self, repo_url: str):
        repo_path = self.get_repo_path(repo_url)
        if repo_path.exists():
            shutil.rmtree(repo_path)
