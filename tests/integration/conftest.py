from __future__ import annotations

import shutil
from pathlib import Path

import git
import pytest

CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache" / "test-repos"


@pytest.fixture
def cached_clone():
    def _get(repo_url: str) -> Path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        repo_name = repo_url.rstrip("/").removesuffix(".git").split("/")[-1]
        temp_clone_path = CACHE_DIR / f"{repo_name}-tmp"
        # A leftover "-tmp" directory is an interrupted clone, never a cache
        # hit: it must be discarded and re-cloned, not reused.
        existing = sorted(
            path for path in CACHE_DIR.glob(f"{repo_name}-*") if path != temp_clone_path
        )
        if existing:
            return existing[0]

        if temp_clone_path.exists():
            shutil.rmtree(temp_clone_path)
        temp_repo = git.Repo.clone_from(repo_url, temp_clone_path, depth=1)
        sha = temp_repo.head.commit.hexsha
        temp_repo.close()

        dest = CACHE_DIR / f"{repo_name}-{sha[:8]}"
        shutil.move(str(temp_clone_path), str(dest))
        return dest

    return _get
