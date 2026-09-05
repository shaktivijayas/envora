import json

from envora.analyzer.models import Confidence
from envora.analyzer.runtime_version import detect_runtime_version


def test_node_engines_field_high_confidence(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"engines": {"node": "20.x"}}), encoding="utf-8")

    detection = detect_runtime_version(tmp_path)

    assert detection.value == "20.x"
    assert detection.confidence == Confidence.HIGH


def test_nvmrc_alone_medium_confidence(tmp_path):
    (tmp_path / ".nvmrc").write_text("18\n", encoding="utf-8")

    detection = detect_runtime_version(tmp_path)

    assert detection.value == "18"
    assert detection.confidence == Confidence.MEDIUM


def test_node_conflicting_sources_manifest_wins_medium_confidence(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"engines": {"node": "20.x"}}), encoding="utf-8")
    (tmp_path / ".nvmrc").write_text("18\n", encoding="utf-8")

    detection = detect_runtime_version(tmp_path)

    assert detection.value == "20.x"
    assert detection.confidence == Confidence.MEDIUM
    assert "conflicting" in detection.evidence[0]


def test_python_requires_python_high_confidence(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.11"\n', encoding="utf-8")

    detection = detect_runtime_version(tmp_path)

    assert detection.value == ">=3.11"
    assert detection.confidence == Confidence.HIGH


def test_python_version_file_alone_medium_confidence(tmp_path):
    (tmp_path / ".python-version").write_text("3.11.4\n", encoding="utf-8")

    detection = detect_runtime_version(tmp_path)

    assert detection.value == "3.11.4"
    assert detection.confidence == Confidence.MEDIUM


def test_malformed_package_json_degrades_to_low(tmp_path):
    (tmp_path / "package.json").write_text("{not valid,,,", encoding="utf-8")

    detection = detect_runtime_version(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
    assert "unparseable" in detection.evidence[0]


def test_no_signal_returns_low_confidence_none(tmp_path):
    detection = detect_runtime_version(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
