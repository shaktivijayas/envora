from envora.analyzer.models import Confidence
from envora.analyzer.services import detect_services


def test_detects_postgres_connection_string(tmp_path):
    src = tmp_path / "db.py"
    src.write_text('DATABASE_URL = "postgres://user:pass@localhost/db"', encoding="utf-8")

    detections = detect_services(tmp_path, [src])

    assert detections[0].value == "postgres"
    assert detections[0].confidence == Confidence.MEDIUM


def test_detects_redis_connection_string(tmp_path):
    src = tmp_path / "cache.py"
    src.write_text('REDIS_URL = "redis://localhost:6379"', encoding="utf-8")

    detections = detect_services(tmp_path, [src])

    assert detections[0].value == "redis"


def test_docker_compose_image_corroborates_and_raises_confidence(tmp_path):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services:\n  db:\n    image: postgres:16\n", encoding="utf-8")
    src = tmp_path / "db.py"
    src.write_text('DATABASE_URL = "postgres://user:pass@db/app"', encoding="utf-8")

    detections = detect_services(tmp_path, [compose, src])

    postgres = next(d for d in detections if d.value == "postgres")
    assert postgres.confidence == Confidence.HIGH
    assert len(postgres.evidence) == 2


def test_compose_image_alone_gives_high_confidence(tmp_path):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services:\n  cache:\n    image: redis:7\n", encoding="utf-8")

    detections = detect_services(tmp_path, [compose])

    assert detections[0].value == "redis"
    assert detections[0].confidence == Confidence.HIGH


def test_no_services_returns_low_confidence_none(tmp_path):
    detections = detect_services(tmp_path, [])

    assert detections[0].value is None
    assert detections[0].confidence == Confidence.LOW
