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


def test_config_but_manifest_silent_gives_low_confidence(tmp_path):
    (tmp_path / "next.config.js").write_text("module.exports = {}", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {}}), encoding="utf-8")

    detection = detect_framework(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
    assert len(detection.evidence) == 2
    assert "next.config.js" in detection.evidence[0]
    assert "package.json" in detection.evidence[1]


def test_conflicting_config_files_gives_low_confidence(tmp_path):
    (tmp_path / "next.config.js").write_text("module.exports = {}", encoding="utf-8")
    (tmp_path / "manage.py").write_text("# django config", encoding="utf-8")

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


def test_pyproject_prose_does_not_substring_match_a_framework(tmp_path):
    # "The next generation API" must not be read as a Next.js signal.
    (tmp_path / "pyproject.toml").write_text(
        '[project]\n'
        'name = "svc"\n'
        'description = "The next generation API"\n'
        'dependencies = ["fastapi>=0.100"]\n',
        encoding="utf-8",
    )

    detection = detect_framework(tmp_path)

    assert detection.value == "fastapi"
    assert detection.confidence == Confidence.MEDIUM


def test_poetry_dependencies_table_is_matched(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.poetry.dependencies]\npython = "^3.11"\nflask = "^3.0"\n',
        encoding="utf-8",
    )

    detection = detect_framework(tmp_path)

    assert detection.value == "flask"


def test_requirements_flask_caching_does_not_detect_flask(tmp_path):
    (tmp_path / "requirements.txt").write_text("flask-caching==2.0\n", encoding="utf-8")

    detection = detect_framework(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW


def test_requirements_django_stubs_ext_does_not_detect_django(tmp_path):
    (tmp_path / "requirements.txt").write_text("django-stubs-ext\n", encoding="utf-8")

    detection = detect_framework(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW


def test_requirements_bare_dependency_is_matched(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "# deps\n-r base.txt\nflask-caching==2.0\nFlask==3.0.0\n", encoding="utf-8"
    )

    detection = detect_framework(tmp_path)

    assert detection.value == "flask"
    assert detection.confidence == Confidence.MEDIUM


def test_pyproject_with_bare_date_value_does_not_crash(tmp_path):
    # TOML parses `2024-01-15` into a datetime.date, which is not JSON
    # serializable by default.
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nreleased = 2024-01-15\n', encoding="utf-8"
    )

    detection = detect_framework(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW


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


def test_non_dict_package_json_degrades_gracefully(tmp_path):
    (tmp_path / "package.json").write_text("null", encoding="utf-8")

    detection = detect_framework(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
    assert "not a JSON object" in detection.evidence[0]


def test_malformed_dependencies_field_degrades_gracefully(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": ["not", "a", "dict"]}), encoding="utf-8"
    )

    detection = detect_framework(tmp_path)

    assert detection.value is None
    assert detection.confidence == Confidence.LOW
    assert "malformed" in detection.evidence[0]
