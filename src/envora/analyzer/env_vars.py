from __future__ import annotations

import re
from pathlib import Path

from envora.analyzer.models import Confidence, Detection
from envora.analyzer.walk import read_text_safe

_SOURCE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"process\.env\.(\w+)"),
    re.compile(r"os\.getenv\(\s*[\"'](\w+)[\"']"),
    re.compile(r"os\.environ\[\s*[\"'](\w+)[\"']\s*\]"),
]

_DOTENV_LINE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=")
_DOTENV_FILENAMES = {".env.example", ".env.sample", ".env.template"}


def detect_env_vars(repo_path: Path, files: list[Path]) -> list[Detection]:
    found: dict[str, list[str]] = {}

    for file_path in files:
        text = read_text_safe(file_path)
        if text is None:
            continue

        rel_path = file_path.relative_to(repo_path).as_posix()

        if file_path.name in _DOTENV_FILENAMES:
            for line in text.splitlines():
                match = _DOTENV_LINE.match(line)
                if match:
                    found.setdefault(match.group(1), []).append(f"{rel_path}: `{line.strip()}`")
            continue

        for pattern in _SOURCE_PATTERNS:
            for match in pattern.finditer(text):
                var_name = match.group(1)
                found.setdefault(var_name, []).append(f"{rel_path}: matched `{match.group(0)}`")

    if not found:
        return [
            Detection(
                value=None,
                confidence=Confidence.LOW,
                evidence=["no environment variable references found in .env.example or source"],
            )
        ]

    detections = []
    for var_name, evidence in sorted(found.items()):
        confidence = Confidence.HIGH if any(e.startswith(".env") for e in evidence) else Confidence.MEDIUM
        detections.append(Detection(value=var_name, confidence=confidence, evidence=evidence))
    return detections
