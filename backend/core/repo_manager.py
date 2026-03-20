"""Repository cloning and management."""
import os
import stat
import shutil
import hashlib
import logging
from pathlib import Path
from git import Repo, InvalidGitRepositoryError
from config.settings import settings

logger = logging.getLogger(__name__)


def _force_remove_readonly(func, path, exc_info):
    """Handle Windows [WinError 5] by clearing read-only flag and retrying."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


class RepoManager:
    def __init__(self):
        self.clone_dir = Path(settings.clone_dir)
        self.clone_dir.mkdir(parents=True, exist_ok=True)

    def _repo_hash(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def _safe_rmtree(self, path: Path):
        """Remove directory tree, handling Windows locked/read-only files."""
        try:
            shutil.rmtree(path, onerror=_force_remove_readonly)
        except Exception as e:
            logger.warning(f"Could not fully remove {path}: {e}")

    def clone(self, repo_url: str, branch: str = "main") -> Path:
        repo_id = self._repo_hash(repo_url)
        target = self.clone_dir / repo_id

        # Reuse existing clone if valid — just fetch latest
        if target.exists():
            try:
                repo = Repo(str(target))
                current_branch = repo.active_branch.name
                if current_branch == branch:
                    logger.info(f"Reusing existing clone at {target}, pulling latest...")
                    repo.remotes.origin.pull()
                    return target
            except (InvalidGitRepositoryError, Exception) as e:
                logger.info(f"Existing clone invalid ({e}), re-cloning...")

            self._safe_rmtree(target)

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
            self._safe_rmtree(repo_path)
