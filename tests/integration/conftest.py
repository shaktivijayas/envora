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
        existing = sorted(CACHE_DIR.glob(f"{repo_name}-*"))
        if existing:
            return existing[0]

        temp_clone_path = CACHE_DIR / f"{repo_name}-tmp"
        if temp_clone_path.exists():
            shutil.rmtree(temp_clone_path)
        temp_repo = git.Repo.clone_from(repo_url, temp_clone_path, depth=1)
        sha = temp_repo.head.commit.hexsha
        temp_repo.close()

        dest = CACHE_DIR / f"{repo_name}-{sha[:8]}"
        shutil.move(str(temp_clone_path), str(dest))
        return dest

    return _get
