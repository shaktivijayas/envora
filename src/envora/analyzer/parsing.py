from __future__ import annotations

import json
import tomllib
from pathlib import Path

from envora.analyzer.walk import MAX_SCAN_FILE_BYTES


def _read_capped(path: Path) -> tuple[str | None, str | None]:
    """Read a manifest, refusing pathologically large files.

    Mirrors walk.read_text_safe: same size cap, same lenient decoding, and it
    never raises - a decode or OS error comes back as an error string.
    """
    try:
        if path.stat().st_size > MAX_SCAN_FILE_BYTES:
            return None, f"{path.name} exceeds {MAX_SCAN_FILE_BYTES} byte size cap, skipped"
        return path.read_text(encoding="utf-8", errors="replace"), None
    except OSError as exc:
        return None, str(exc)


def parse_json(path: Path) -> tuple[dict | None, str | None]:
    text, error = _read_capped(path)
    if text is None:
        return None, error
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def parse_toml(path: Path) -> tuple[dict | None, str | None]:
    text, error = _read_capped(path)
    if text is None:
        return None, error
    try:
        return tomllib.loads(text), None
    except tomllib.TOMLDecodeError as exc:
        return None, str(exc)
