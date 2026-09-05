from __future__ import annotations

import re
from pathlib import Path

from envora.analyzer.models import Confidence, Detection
from envora.analyzer.parsing import parse_json, parse_toml
from envora.analyzer.walk import read_text_safe

_VERSION_PATTERN = re.compile(r"(\d+(?:\.\d+)*)")


def _node_manifest_version(repo_path: Path) -> tuple[str | None, str | None]:
    package_json = repo_path / "package.json"
    if not package_json.is_file():
        return None, None
    data, error = parse_json(package_json)
    if error is not None:
        return None, f"package.json present but unparseable: {error}"
    if not isinstance(data, dict):
        return None, "package.json present but not a JSON object"
    engines = data.get("engines", {})
    node_version = engines.get("node") if isinstance(engines, dict) else None
    if node_version:
        return node_version, f'engines.node = "{node_version}" in package.json'
    return None, None


def _node_pin_file(repo_path: Path) -> tuple[str | None, str | None]:
    nvmrc = repo_path / ".nvmrc"
    if not nvmrc.is_file():
        return None, None
    text = (read_text_safe(nvmrc) or "").strip()
    match = _VERSION_PATTERN.search(text)
    if not match:
        return None, None
    return match.group(1), f'.nvmrc = "{text}"'


def _python_manifest_version(repo_path: Path) -> tuple[str | None, str | None]:
    pyproject = repo_path / "pyproject.toml"
    if not pyproject.is_file():
        return None, None
    data, error = parse_toml(pyproject)
    if error is not None:
        return None, f"pyproject.toml present but unparseable: {error}"
    if not isinstance(data, dict):
        return None, "pyproject.toml present but not a TOML table"
    project = data.get("project", {})
    requires_python = project.get("requires-python") if isinstance(project, dict) else None
    if requires_python:
        return requires_python, f'requires-python = "{requires_python}" in pyproject.toml'
    tool = data.get("tool", {})
    poetry = tool.get("poetry", {}) if isinstance(tool, dict) else {}
    poetry_deps = poetry.get("dependencies", {}) if isinstance(poetry, dict) else {}
    poetry_python = poetry_deps.get("python") if isinstance(poetry_deps, dict) else None
    if poetry_python:
        return poetry_python, f'[tool.poetry.dependencies] python = "{poetry_python}" in pyproject.toml'
    return None, None


def _python_pin_file(repo_path: Path) -> tuple[str | None, str | None]:
    pin_file = repo_path / ".python-version"
    if not pin_file.is_file():
        return None, None
    text = (read_text_safe(pin_file) or "").strip()
    if not text:
        return None, None
    return text, f'.python-version = "{text}"'


def detect_runtime_version(repo_path: Path) -> Detection:
    fallback_error_evidence = None

    for manifest_fn, pin_fn in (
        (_node_manifest_version, _node_pin_file),
        (_python_manifest_version, _python_pin_file),
    ):
        manifest_value, manifest_evidence = manifest_fn(repo_path)
        if manifest_evidence and manifest_value is None:
            if fallback_error_evidence is None:
                fallback_error_evidence = manifest_evidence
            # Don't return yet; check this ecosystem's pin file, then try the next ecosystem

        pin_value, pin_evidence = pin_fn(repo_path)

        if manifest_value and pin_value:
            if manifest_value == pin_value:
                return Detection(
                    value=manifest_value,
                    confidence=Confidence.HIGH,
                    evidence=[manifest_evidence, pin_evidence],
                )
            return Detection(
                value=manifest_value,
                confidence=Confidence.MEDIUM,
                evidence=[
                    f"conflicting runtime version sources: {manifest_evidence} vs {pin_evidence}; "
                    "manifest source takes precedence",
                ],
            )

        if manifest_value:
            return Detection(value=manifest_value, confidence=Confidence.HIGH, evidence=[manifest_evidence])

        if pin_value:
            return Detection(value=pin_value, confidence=Confidence.MEDIUM, evidence=[pin_evidence])

    if fallback_error_evidence:
        return Detection(
            value=None,
            confidence=Confidence.LOW,
            evidence=[fallback_error_evidence],
        )

    return Detection(
        value=None,
        confidence=Confidence.LOW,
        evidence=["no runtime version signal found (engines.node, .nvmrc, requires-python, .python-version)"],
    )
