from envora.analyzer.env_vars import detect_env_vars
from envora.analyzer.models import Confidence


def test_detects_env_example_vars_at_high_confidence(tmp_path):
    env_file = tmp_path / ".env.example"
    env_file.write_text("DATABASE_URL=postgres://localhost/db\nPORT=3000\n", encoding="utf-8")

    detections = detect_env_vars(tmp_path, [env_file])

    values = {d.value for d in detections}
    assert values == {"DATABASE_URL", "PORT"}
    assert all(d.confidence == Confidence.HIGH for d in detections)


def test_detects_process_env_reference_in_source(tmp_path):
    src = tmp_path / "config.js"
    src.write_text("const port = process.env.PORT;", encoding="utf-8")

    detections = detect_env_vars(tmp_path, [src])

    assert detections[0].value == "PORT"
    assert detections[0].confidence == Confidence.MEDIUM


def test_detects_os_getenv_reference_in_source(tmp_path):
    src = tmp_path / "config.py"
    src.write_text('secret = os.getenv("SECRET_KEY")', encoding="utf-8")

    detections = detect_env_vars(tmp_path, [src])

    assert detections[0].value == "SECRET_KEY"


def test_detects_os_environ_bracket_reference(tmp_path):
    src = tmp_path / "config.py"
    src.write_text('db = os.environ["DATABASE_URL"]', encoding="utf-8")

    detections = detect_env_vars(tmp_path, [src])

    assert detections[0].value == "DATABASE_URL"


def test_no_env_var_references_returns_low_confidence_none(tmp_path):
    detections = detect_env_vars(tmp_path, [])

    assert detections[0].value is None
    assert detections[0].confidence == Confidence.LOW
