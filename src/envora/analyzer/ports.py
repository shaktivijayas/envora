from __future__ import annotations

import re
from pathlib import Path

from envora.analyzer.models import Confidence, Detection
from envora.analyzer.walk import read_text_safe

# Confidence tiers mirror env_vars.py/services.py: HIGH is reserved for a
# declared binding (EXPOSE, a compose mapping, a literal port handed to
# .listen()), MEDIUM is a source-code match that only implies a port, LOW is a
# match inside documentation.
_GENERAL_PORT_PATTERNS: list[tuple[re.Pattern[str], Confidence]] = [
    # A literal port passed to a server bind call is a declaration.
    (re.compile(r"app\.listen\(\s*(\d{2,5})"), Confidence.HIGH),
    (re.compile(r"\.listen\(\s*(?:port\s*=\s*)?(\d{2,5})"), Confidence.HIGH),
    # Everything below is inferred from surrounding source, not declared.
    (re.compile(r"PORT\s*[=:]\s*(\d{2,5})"), Confidence.MEDIUM),
    (re.compile(r"PORT\s*\|\|\s*(\d{2,5})"), Confidence.MEDIUM),
    (re.compile(r"uvicorn\.run\([^)]*port\s*=\s*(\d{2,5})"), Confidence.MEDIUM),
    (re.compile(r"--port[= ](\d{2,5})"), Confidence.MEDIUM),
    (re.compile(r'\.Run\(":(\d{2,5})"\)'), Confidence.MEDIUM),
    (re.compile(r"net\.Listen\([^)]*:(\d{2,5})"), Confidence.MEDIUM),
    (re.compile(r"runserver\s+(?:\S*:)?(\d{2,5})"), Confidence.MEDIUM),
]

_DOCKERFILE_PORT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"EXPOSE\s+(\d{2,5})"),
]

_COMPOSE_PORT_PATTERN: re.Pattern[str] = re.compile(r'^-\s*["\']*(\d{2,5}):(\d{2,5})')

_DOC_SUFFIXES = {".md", ".mdx", ".rst"}

_CONFIDENCE_RANK: dict[Confidence, int] = {
    Confidence.LOW: 0,
    Confidence.MEDIUM: 1,
    Confidence.HIGH: 2,
}


def _is_doc_file(path: Path) -> bool:
    return path.name.startswith("README") or path.suffix.lower() in _DOC_SUFFIXES


def detect_ports(repo_path: Path, files: list[Path]) -> list[Detection]:
    found: dict[str, list[str]] = {}
    confidence_map: dict[str, Confidence] = {}

    def record(port: str, evidence: str, confidence: Confidence) -> None:
        found.setdefault(port, []).append(evidence)
        current = confidence_map.get(port)
        if current is None or _CONFIDENCE_RANK[confidence] > _CONFIDENCE_RANK[current]:
            confidence_map[port] = confidence

    for file_path in files:
        text = read_text_safe(file_path)
        if text is None:
            continue

        rel_path = file_path.relative_to(repo_path).as_posix()
        # Documentation describes a port, it does not bind one.
        is_doc = _is_doc_file(file_path)

        if file_path.name == "Dockerfile":
            for pattern in _DOCKERFILE_PORT_PATTERNS:
                for match in pattern.finditer(text):
                    port = match.group(1)
                    evidence_line = f"{rel_path}: matched `{match.group(0).strip()}`"
                    record(port, evidence_line, Confidence.HIGH)
        elif file_path.name in {"docker-compose.yml", "docker-compose.yaml"}:
            # Line-by-line matching for compose port mappings
            for line in text.split("\n"):
                stripped = line.strip()
                match = _COMPOSE_PORT_PATTERN.match(stripped)
                if match:
                    port = match.group(1)
                    evidence_line = f"{rel_path}: matched `{stripped}`"
                    record(port, evidence_line, Confidence.HIGH)
        else:
            # General source code patterns
            for pattern, confidence in _GENERAL_PORT_PATTERNS:
                for match in pattern.finditer(text):
                    port = match.group(1)
                    evidence_line = f"{rel_path}: matched `{match.group(0).strip()}`"
                    record(port, evidence_line, Confidence.LOW if is_doc else confidence)

    if not found:
        return [
            Detection(
                value=None,
                confidence=Confidence.LOW,
                evidence=["no port-binding pattern found in source or Docker config"],
            )
        ]

    return [
        Detection(
            value=port,
            confidence=confidence_map.get(port, Confidence.MEDIUM),
            evidence=evidence,
        )
        for port, evidence in sorted(found.items())
    ]
