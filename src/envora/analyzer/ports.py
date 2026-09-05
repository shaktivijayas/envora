from __future__ import annotations

import re
from pathlib import Path

from envora.analyzer.models import Confidence, Detection
from envora.analyzer.walk import read_text_safe

_GENERAL_PORT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"app\.listen\(\s*(\d{2,5})"),
    re.compile(r"\.listen\(\s*(?:port\s*=\s*)?(\d{2,5})"),
    re.compile(r"PORT\s*[=:]\s*(\d{2,5})"),
    re.compile(r"uvicorn\.run\([^)]*port\s*=\s*(\d{2,5})"),
    re.compile(r"--port[= ](\d{2,5})"),
    re.compile(r'\.Run\(":(\d{2,5})"\)'),
    re.compile(r"net\.Listen\([^)]*:(\d{2,5})"),
]

_DOCKER_FILENAMES = {"Dockerfile", "docker-compose.yml", "docker-compose.yaml"}
_DOCKER_PORT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"EXPOSE\s+(\d{2,5})"),
    re.compile(r":(\d{2,5})(?=[\"'\s]|$)"),
]


def detect_ports(repo_path: Path, files: list[Path]) -> list[Detection]:
    found: dict[str, list[str]] = {}

    for file_path in files:
        text = read_text_safe(file_path)
        if text is None:
            continue

        rel_path = file_path.relative_to(repo_path).as_posix()
        patterns = _DOCKER_PORT_PATTERNS if file_path.name in _DOCKER_FILENAMES else _GENERAL_PORT_PATTERNS

        for pattern in patterns:
            for match in pattern.finditer(text):
                port = match.group(1)
                evidence_line = f"{rel_path}: matched `{match.group(0).strip()}`"
                found.setdefault(port, []).append(evidence_line)

    if not found:
        return [
            Detection(
                value=None,
                confidence=Confidence.LOW,
                evidence=["no port-binding pattern found in source or Docker config"],
            )
        ]

    return [
        Detection(value=port, confidence=Confidence.HIGH, evidence=evidence)
        for port, evidence in sorted(found.items())
    ]
