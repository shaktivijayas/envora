from __future__ import annotations

import re
from pathlib import Path

from envora.analyzer.models import Confidence, Detection
from envora.analyzer.walk import read_text_safe

_CONNECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"postgres(?:ql)?://"), "postgres"),
    (re.compile(r"redis://"), "redis"),
    (re.compile(r"mongodb(?:\+srv)?://"), "mongodb"),
    (re.compile(r"mysql://"), "mysql"),
]

_COMPOSE_FILENAMES = {"docker-compose.yml", "docker-compose.yaml"}
_COMPOSE_IMAGE_LINE = re.compile(r"image:\s*[\"']?([\w./-]+)")

_IMAGE_TO_SERVICE: dict[str, str] = {
    "postgres": "postgres",
    "redis": "redis",
    "mongo": "mongodb",
    "mysql": "mysql",
    "mariadb": "mysql",
}


def _service_from_image(image: str) -> str | None:
    base = image.split("/")[-1].split(":")[0]
    return _IMAGE_TO_SERVICE.get(base)


def detect_services(repo_path: Path, files: list[Path]) -> list[Detection]:
    found: dict[str, list[str]] = {}

    for file_path in files:
        text = read_text_safe(file_path)
        if text is None:
            continue

        rel_path = file_path.relative_to(repo_path).as_posix()

        for pattern, service in _CONNECTION_PATTERNS:
            if pattern.search(text):
                found.setdefault(service, []).append(f"{rel_path}: connection string pattern `{service}://`")

        if file_path.name in _COMPOSE_FILENAMES:
            for match in _COMPOSE_IMAGE_LINE.finditer(text):
                service = _service_from_image(match.group(1))
                if service:
                    found.setdefault(service, []).append(f"{rel_path}: `image: {match.group(1)}`")

    if not found:
        return [
            Detection(
                value=None,
                confidence=Confidence.LOW,
                evidence=["no service connection strings or docker-compose service images found"],
            )
        ]

    detections = []
    for service, evidence in sorted(found.items()):
        confidence = Confidence.HIGH if any("image:" in e for e in evidence) else Confidence.MEDIUM
        detections.append(Detection(value=service, confidence=confidence, evidence=evidence))
    return detections
