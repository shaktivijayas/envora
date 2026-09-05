from __future__ import annotations

import json
import tomllib
from pathlib import Path


def parse_json(path: Path) -> tuple[dict | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return None, str(exc)
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def parse_toml(path: Path) -> tuple[dict | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return None, str(exc)
    try:
        return tomllib.loads(text), None
    except tomllib.TOMLDecodeError as exc:
        return None, str(exc)
