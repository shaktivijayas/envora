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
    confidence_map: dict[str, Confidence] = {}

    for file_path in files:
        text = read_text_safe(file_path)
        if text is None:
            continue

        rel_path = file_path.relative_to(repo_path).as_posix()

        if file_path.name in _DOTENV_FILENAMES:
            for line in text.splitlines():
                match = _DOTENV_LINE.match(line)
                if match:
                    var_name = match.group(1)
                    found.setdefault(var_name, []).append(f"{rel_path}: `{line.strip()}`")
                    # Track HIGH confidence for dotenv files, don't override if already set to HIGH
                    if var_name not in confidence_map or confidence_map[var_name] != Confidence.HIGH:
                        confidence_map[var_name] = Confidence.HIGH
            continue

        if file_path.name.startswith("README"):
            for line in text.splitlines():
                match = _DOTENV_LINE.match(line)
                if match:
                    var_name = match.group(1)
                    found.setdefault(var_name, []).append(f"{rel_path}: `{line.strip()}`")
                    # Track MEDIUM confidence for README files, don't override if already set to HIGH
                    if var_name not in confidence_map:
                        confidence_map[var_name] = Confidence.MEDIUM
            continue

        for pattern in _SOURCE_PATTERNS:
            for match in pattern.finditer(text):
                var_name = match.group(1)
                found.setdefault(var_name, []).append(f"{rel_path}: matched `{match.group(0)}`")
                # Track MEDIUM confidence for source patterns, don't override if already set to HIGH or MEDIUM
                if var_name not in confidence_map:
                    confidence_map[var_name] = Confidence.MEDIUM

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
        confidence = confidence_map.get(var_name, Confidence.MEDIUM)
        detections.append(Detection(value=var_name, confidence=confidence, evidence=evidence))
    return detections
