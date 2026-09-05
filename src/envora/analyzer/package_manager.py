from __future__ import annotations

from pathlib import Path

from envora.analyzer.models import Confidence, Detection

_LOCKFILE_MAP: list[tuple[str, str]] = [
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("package-lock.json", "npm"),
    ("poetry.lock", "poetry"),
    ("Pipfile.lock", "pipenv"),
]


def detect_package_manager(repo_path: Path) -> Detection:
    for lockfile, manager in _LOCKFILE_MAP:
        if (repo_path / lockfile).is_file():
            return Detection(
                value=manager,
                confidence=Confidence.HIGH,
                evidence=[f"{lockfile} present at repo root"],
            )

    if (repo_path / "package.json").is_file():
        return Detection(
            value="npm",
            confidence=Confidence.LOW,
            evidence=["no lockfile found, defaulting to npm convention"],
        )

    if (repo_path / "requirements.txt").is_file():
        return Detection(
            value="pip",
            confidence=Confidence.MEDIUM,
            evidence=["requirements.txt present at repo root"],
        )

    return Detection(
        value=None,
        confidence=Confidence.LOW,
        evidence=["no recognized lockfile or manifest found"],
    )
