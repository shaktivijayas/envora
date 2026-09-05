from envora.analyzer.models import Confidence
from envora.analyzer.ports import detect_ports


def test_detects_express_listen_call(tmp_path):
    app = tmp_path / "index.js"
    app.write_text("app.listen(3000, () => console.log('up'))", encoding="utf-8")

    detections = detect_ports(tmp_path, [app])

    assert detections[0].value == "3000"
    assert detections[0].confidence == Confidence.HIGH


def test_detects_uvicorn_port_kwarg(tmp_path):
    main = tmp_path / "main.py"
    main.write_text("uvicorn.run(app, host='0.0.0.0', port=8000)", encoding="utf-8")

    detections = detect_ports(tmp_path, [main])

    assert {d.value for d in detections} == {"8000"}
    # Inferred from source, not a declared binding.
    assert detections[0].confidence == Confidence.MEDIUM


def test_detects_dockerfile_expose(tmp_path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM node:20\nEXPOSE 4000\n", encoding="utf-8")

    detections = detect_ports(tmp_path, [dockerfile])

    # Must detect EXPOSE 4000 but NOT match :20 from base image tag
    assert {d.value for d in detections} == {"4000"}
    assert detections[0].confidence == Confidence.HIGH


def test_ignores_bare_numbers_that_are_not_binding_contexts(tmp_path):
    src = tmp_path / "constants.py"
    src.write_text("MAX_RETRIES = 5000\nTIMEOUT = 30000\n", encoding="utf-8")

    detections = detect_ports(tmp_path, [src])

    assert detections[0].value is None
    assert detections[0].confidence == Confidence.LOW


def test_no_files_returns_low_confidence_none(tmp_path):
    detections = detect_ports(tmp_path, [])

    assert detections[0].value is None
    assert detections[0].confidence == Confidence.LOW


def test_detects_docker_compose_port_mapping(tmp_path):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services:\n  app:\n    ports:\n      - \"8080:80\"\n", encoding="utf-8")

    detections = detect_ports(tmp_path, [compose])

    assert {d.value for d in detections} == {"8080"}
    assert detections[0].confidence == Confidence.HIGH


def test_detects_django_runserver(tmp_path):
    manage = tmp_path / "manage.py"
    manage.write_text("python manage.py runserver 8000", encoding="utf-8")

    detections = detect_ports(tmp_path, [manage])

    assert {d.value for d in detections} == {"8000"}
    assert detections[0].confidence == Confidence.MEDIUM


def test_detects_env_port_with_fallback_default(tmp_path):
    # Extremely common Node/Express idiom: `const port = process.env.PORT || 5006`
    index = tmp_path / "index.js"
    index.write_text(
        "const port = process.env.PORT || 5006\napp.listen(port, () => {})",
        encoding="utf-8",
    )

    detections = detect_ports(tmp_path, [index])

    assert {d.value for d in detections} == {"5006"}
    # The literal is a fallback default in source, not a declared binding.
    assert all(d.confidence == Confidence.MEDIUM for d in detections)


def test_readme_mentioned_port_is_low_confidence(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("Set PORT=3000 before running the server.\n", encoding="utf-8")

    detections = detect_ports(tmp_path, [readme])

    assert {d.value for d in detections} == {"3000"}
    assert detections[0].confidence == Confidence.LOW


def test_declared_binding_outranks_documentation_for_same_port(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("Set PORT=3000 before running.\n", encoding="utf-8")
    index = tmp_path / "index.js"
    index.write_text("app.listen(3000)\n", encoding="utf-8")

    detections = detect_ports(tmp_path, [readme, index])

    assert {d.value for d in detections} == {"3000"}
    assert detections[0].confidence == Confidence.HIGH
    assert any("README.md" in line for line in detections[0].evidence)
    assert any("index.js" in line for line in detections[0].evidence)


def test_env_style_port_assignment_in_source_is_medium(tmp_path):
    src = tmp_path / "settings.py"
    src.write_text("PORT = 8081\n", encoding="utf-8")

    detections = detect_ports(tmp_path, [src])

    assert {d.value for d in detections} == {"8081"}
    assert detections[0].confidence == Confidence.MEDIUM


def test_go_run_and_net_listen_are_medium(tmp_path):
    src = tmp_path / "server.go"
    src.write_text('r.Run(":8080")\nnet.Listen("tcp", ":9090")\n', encoding="utf-8")

    detections = detect_ports(tmp_path, [src])

    assert {d.value for d in detections} == {"8080", "9090"}
    assert all(d.confidence == Confidence.MEDIUM for d in detections)


def test_port_flag_is_medium(tmp_path):
    script = tmp_path / "start.sh"
    script.write_text("exec gunicorn app:app --port 8000\n", encoding="utf-8")

    detections = detect_ports(tmp_path, [script])

    assert {d.value for d in detections} == {"8000"}
    assert detections[0].confidence == Confidence.MEDIUM
