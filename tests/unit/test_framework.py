import json

from envora.analyzer.framework import detect_framework
from envora.analyzer.models import Confidence


def test_config_and_manifest_agree_gives_high_confidence(tmp_path):
    (tmp_path / "next.config.js").write_text("module.exports = {}", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"next": "14.0.0"}}), encoding="utf-8"
    )

    detection = detect_framework(tmp_path)

    assert detection.value == "nextjs"
    assert detection.confidence == Confidence.HIGH
    assert len(detection.evidence) == 2


def test_config_alone_gives_medium_confidence(tmp_path):
    (tmp_path / "manage.py").write_text("# django manage.py", encoding="utf-8")

    detection = detect_framework(tmp_path)

    assert detection.value == "django"
    assert detection.confidence == Confidence.MEDIUM


def test_manifest_alone_gives_medium_confidence(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"next": "14.0.0"}}), encoding="utf-8"
    )

    detection = detect_framework(tmp_path)

    assert detection.value == "nextjs"
    assert detection.confidence == Confidence.MEDIUM


def test_conflicting_config_and_manifest_gives_low_confidence(tmp_path):
    (tmp_path / "next.config.js").write_text("module.exports = {}", encoding="utf-8")
    (tmp_path / "manage.py").write_text("# stale leftover", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {}}), encoding="utf-8")

    detection = detect_framework(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
    assert "conflicting" in detection.evidence[0]


def test_fastapi_detected_via_pyproject_dependency(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["fastapi>=0.100"]\n', encoding="utf-8"
    )

    detection = detect_framework(tmp_path)

    assert detection.value == "fastapi"
    assert detection.confidence == Confidence.MEDIUM


def test_malformed_package_json_degrades_to_low_with_evidence(tmp_path):
    (tmp_path / "package.json").write_text("{not valid json,,,", encoding="utf-8")

    detection = detect_framework(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
    assert "unparseable" in detection.evidence[0]


def test_no_signal_returns_low_confidence_none(tmp_path):
    detection = detect_framework(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
