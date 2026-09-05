from __future__ import annotations

import os
import shutil
import stat
import sys
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path

import git


class CloneError(Exception):
    def __init__(self, url: str, cause: Exception) -> None:
        super().__init__(f"failed to clone {url}: {cause}")
        self.url = url
        self.cause = cause


def _handle_remove_error(func, path, _exc):
    """rmtree error handler: retry read-only paths (common on Windows).

    Signature-compatible with both `onerror` (3.11) and `onexc` (3.12+),
    which differ only in the third argument. Never raises: a scratch
    directory that survives cleanup is a leak, not a failure worth
    reporting to the caller.
    """
    try:
        os.chmod(path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
        func(path)
    except Exception:  # cleanup is best effort
        pass


@dataclass
class ClonedRepo:
    path: Path
    branch: str
    url: str

    def __enter__(self) -> "ClonedRepo":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # A cleanup failure must never escape: it would crash the CLI after a
        # successful analysis and throw away the computed result. The worst
        # case is an orphaned scratch directory, which we only warn about.
        try:
            if sys.version_info >= (3, 12):
                shutil.rmtree(self.path, onexc=_handle_remove_error)
            else:
                shutil.rmtree(self.path, onerror=_handle_remove_error)
        except Exception as exc:  # cleanup is best effort
            warnings.warn(
                f"could not remove temporary clone at {self.path}: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )


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
