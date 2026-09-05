from __future__ import annotations

from pathlib import Path

from envora.analyzer.models import Confidence, Detection

# Root-level manifests only (no subdirectory/monorepo walk — see spec
# Non-goals). Each manifest found produces its own HIGH-confidence
# Detection; when multiple stacks' manifests are present, all of them
# are returned — no single value is chosen among them.
_STACK_MANIFESTS: list[tuple[str, tuple[str, ...]]] = [
    ("node", ("package.json",)),
    ("python", ("pyproject.toml", "setup.py", "requirements.txt")),
    ("rust", ("Cargo.toml",)),
    ("go", ("go.mod",)),
    ("java", ("pom.xml", "build.gradle")),
]


def detect_stack(repo_path: Path) -> list[Detection]:
    detections: list[Detection] = []
    for stack_name, manifests in _STACK_MANIFESTS:
        found = [m for m in manifests if (repo_path / m).is_file()]
        if found:
            detections.append(
                Detection(
                    value=stack_name,
                    confidence=Confidence.HIGH,
                    evidence=[f"{m} present at repo root" for m in found],
                )
            )

    if not detections:
        return [
            Detection(
                value=None,
                confidence=Confidence.LOW,
                evidence=[
                    "no package.json, pyproject.toml, setup.py, requirements.txt, "
                    "Cargo.toml, go.mod, pom.xml, or build.gradle found at repo root",
                ],
            )
        ]
    return detections
