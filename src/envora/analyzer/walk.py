from __future__ import annotations

import os
from pathlib import Path

EXCLUDED_DIRS: set[str] = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "venv",
    ".venv",
    "__pycache__",
    ".next",
    "target",
    "vendor",
}

MAX_SCAN_FILE_BYTES = 1_000_000


def walk_repo(repo_path: Path) -> list[Path]:
    files: list[Path] = []
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for filename in filenames:
            files.append(Path(root) / filename)
    return files


def read_text_safe(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_SCAN_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
