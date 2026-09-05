from envora.analyzer.models import Confidence
from envora.analyzer.stack import detect_stack


def test_detects_node_from_package_json(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    detections = detect_stack(tmp_path)

    assert len(detections) == 1
    assert detections[0].value == "node"
    assert detections[0].confidence == Confidence.HIGH


def test_detects_python_from_pyproject_toml(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    detections = detect_stack(tmp_path)

    assert detections[0].value == "python"
    assert detections[0].confidence == Confidence.HIGH


def test_detects_rust_from_cargo_toml(tmp_path):
    (tmp_path / "Cargo.toml").write_text("[package]\nname='x'\n", encoding="utf-8")

    detections = detect_stack(tmp_path)

    assert detections[0].value == "rust"


def test_detects_go_from_go_mod(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/x\n", encoding="utf-8")

    detections = detect_stack(tmp_path)

    assert detections[0].value == "go"


def test_detects_multiple_stacks_when_both_manifests_present(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    detections = detect_stack(tmp_path)

    values = {d.value for d in detections}
    assert values == {"node", "python"}


def test_no_manifest_found_returns_low_confidence_none(tmp_path):
    detections = detect_stack(tmp_path)

    assert len(detections) == 1
    assert detections[0].value is None
    assert detections[0].confidence == Confidence.LOW
