from __future__ import annotations

import os
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

import git


class CloneError(Exception):
    def __init__(self, url: str, cause: Exception) -> None:
        super().__init__(f"failed to clone {url}: {cause}")
        self.url = url
        self.cause = cause


def _handle_remove_error(func, path, exc_info):
    """Error handler for shutil.rmtree to fix permission issues on Windows."""
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
        func(path)


@dataclass
class ClonedRepo:
    path: Path
    branch: str
    url: str

    def __enter__(self) -> "ClonedRepo":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        shutil.rmtree(self.path, onerror=_handle_remove_error, ignore_errors=False)


def clone(url: str) -> ClonedRepo:
    temp_dir = Path(tempfile.mkdtemp(prefix="envora-"))
    try:
        repo = git.Repo.clone_from(url, temp_dir, depth=1)
        branch = repo.active_branch.name
        del repo
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise CloneError(url, exc) from exc
    return ClonedRepo(path=temp_dir, branch=branch, url=url)
