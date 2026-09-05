import pytest

from envora.analyzer.models import Confidence
from envora.analyzer.package_manager import detect_package_manager


@pytest.mark.parametrize(
    ("lockfile", "expected_manager"),
    [
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("package-lock.json", "npm"),
        ("poetry.lock", "poetry"),
        ("Pipfile.lock", "pipenv"),
    ],
)
def test_lockfile_maps_to_high_confidence_manager(tmp_path, lockfile, expected_manager):
    (tmp_path / lockfile).write_text("", encoding="utf-8")

    detection = detect_package_manager(tmp_path)

    assert detection.value == expected_manager
    assert detection.confidence == Confidence.HIGH


def test_package_json_with_no_lockfile_defaults_to_npm_at_low_confidence(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    detection = detect_package_manager(tmp_path)

    assert detection.value == "npm"
    assert detection.confidence == Confidence.LOW
    assert "no lockfile found" in detection.evidence[0]


def test_bare_requirements_txt_maps_to_pip(tmp_path):
    (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")

    detection = detect_package_manager(tmp_path)

    assert detection.value == "pip"
    assert detection.confidence == Confidence.MEDIUM


def test_no_manifest_or_lockfile_returns_low_confidence_none(tmp_path):
    detection = detect_package_manager(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
