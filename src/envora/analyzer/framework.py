from __future__ import annotations

import json
from pathlib import Path

from envora.analyzer.models import Confidence, Detection
from envora.analyzer.parsing import parse_json, parse_toml
from envora.analyzer.walk import read_text_safe

_CONFIG_FRAMEWORKS: list[tuple[str, str]] = [
    ("next.config.js", "nextjs"),
    ("next.config.mjs", "nextjs"),
    ("next.config.ts", "nextjs"),
    ("manage.py", "django"),
]

_MANIFEST_DEP_FRAMEWORKS: dict[str, str] = {
    "next": "nextjs",
    "django": "django",
    "fastapi": "fastapi",
    "flask": "flask",
}


def _config_signal(repo_path: Path) -> tuple[str, str] | tuple[None, str] | None:
    found_configs: list[tuple[str, str]] = []
    for filename, framework in _CONFIG_FRAMEWORKS:
        if (repo_path / filename).is_file():
            found_configs.append((framework, filename))

    if not found_configs:
        return None

    # Check for conflicts among config files
    frameworks = {framework for framework, _ in found_configs}
    if len(frameworks) > 1:
        # Multiple conflicting config files
        config_strs = [f'"{filename}"' for _, filename in found_configs]
        frameworks_str = ", ".join(f'"{fw}"' for fw in sorted(frameworks))
        return None, f"conflicting framework signals: {', '.join(config_strs)} indicate different frameworks: {frameworks_str}"

    # All config files agree on the same framework
    framework, filename = found_configs[0]
    return framework, f"{filename} present at repo root"


def _manifest_signal(repo_path: Path) -> tuple[str | None, str | None, str]:
    """
    Returns (framework, evidence, status) where status is one of:
    - "found": framework dependency found
    - "silent": manifest file present but no known framework found
    - "absent": no manifest file found
    - "error": manifest file present but unparseable or malformed
    """
    package_json = repo_path / "package.json"
    if package_json.is_file():
        data, error = parse_json(package_json)
        if error is not None:
            return None, f"package.json present but unparseable: {error}", "error"
        # Guard against non-dict JSON (e.g., null, [], etc.)
        if not isinstance(data, dict):
            return None, "package.json present but not a JSON object", "error"
        # Guard against dependencies/devDependencies not being dicts
        deps_dict = data.get("dependencies", {})
        devdeps_dict = data.get("devDependencies", {})
        if not isinstance(deps_dict, dict) or not isinstance(devdeps_dict, dict):
            return None, "package.json present but dependencies field is malformed", "error"
        deps = {**deps_dict, **devdeps_dict}
        for dep_name, framework in _MANIFEST_DEP_FRAMEWORKS.items():
            if dep_name in deps:
                return framework, f'"{dep_name}" listed in package.json dependencies', "found"
        # Manifest present but no known framework found
        return None, "package.json present but lists no known framework dependencies", "silent"

    pyproject = repo_path / "pyproject.toml"
    if pyproject.is_file():
        data, error = parse_toml(pyproject)
        if error is not None:
            return None, f"pyproject.toml present but unparseable: {error}", "error"
        # Guard against non-dict TOML
        if not isinstance(data, dict):
            return None, "pyproject.toml present but not a valid TOML object", "error"
        haystack = json.dumps(data).lower()
        for dep_name, framework in _MANIFEST_DEP_FRAMEWORKS.items():
            if dep_name in haystack:
                return framework, f'"{dep_name}" referenced in pyproject.toml', "found"
        # Manifest present but no known framework found
        return None, "pyproject.toml present but references no known frameworks", "silent"

    requirements = repo_path / "requirements.txt"
    if requirements.is_file():
        text = (read_text_safe(requirements) or "").lower()
        for dep_name, framework in _MANIFEST_DEP_FRAMEWORKS.items():
            if dep_name in text:
                return framework, f'"{dep_name}" referenced in requirements.txt', "found"
        # Manifest present but no known framework found
        return None, "requirements.txt present but lists no known framework dependencies", "silent"

    return None, None, "absent"


def detect_framework(repo_path: Path) -> Detection:
    config = _config_signal(repo_path)
    manifest_framework, manifest_evidence, manifest_status = _manifest_signal(repo_path)

    # Handle config conflicts (config returns (None, error_message))
    config_error = None
    config_framework = None
    config_evidence = None
    if config:
        if config[0] is None:
            config_error = config[1]
        else:
            config_framework, config_evidence = config

    # Handle unparseable/malformed manifest (error status)
    if manifest_status == "error":
        evidence = [manifest_evidence]
        if config_error:
            evidence.append(config_error)
        elif config_evidence:
            evidence.append(config_evidence)
        return Detection(value=None, confidence=Confidence.LOW, evidence=evidence)

    # Handle conflicting config files
    if config_error:
        evidence = [config_error]
        if manifest_status == "silent":
            evidence.append(manifest_evidence)
        elif manifest_framework:
            evidence.append(manifest_evidence)
        return Detection(value=None, confidence=Confidence.LOW, evidence=evidence)

    # Config and manifest both found - check if they agree
    if config_framework and manifest_framework:
        if config_framework == manifest_framework:
            return Detection(
                value=config_framework,
                confidence=Confidence.HIGH,
                evidence=[config_evidence, manifest_evidence],
            )
        # Config and manifest disagree on which framework
        return Detection(
            value=None,
            confidence=Confidence.LOW,
            evidence=[
                f"conflicting framework signals: {config_evidence} indicates {config_framework}, "
                f"but {manifest_evidence} indicates {manifest_framework}",
            ],
        )

    # Config present, manifest silent (present but doesn't confirm) - LOW confidence
    if config_framework and manifest_status == "silent":
        return Detection(
            value=None,
            confidence=Confidence.LOW,
            evidence=[config_evidence, manifest_evidence],
        )

    # Config alone (manifest absent) - MEDIUM confidence
    if config_framework and manifest_status == "absent":
        return Detection(value=config_framework, confidence=Confidence.MEDIUM, evidence=[config_evidence])

    # Manifest alone - MEDIUM confidence
    if manifest_framework:
        return Detection(value=manifest_framework, confidence=Confidence.MEDIUM, evidence=[manifest_evidence])

    # No signals at all
    return Detection(
        value=None,
        confidence=Confidence.LOW,
        evidence=["no framework config file or manifest dependency match found"],
    )
