import json

from envora.analyzer.analyzer import analyze
from envora.analyzer.models import Confidence


def test_analyze_combines_all_detectors_for_a_node_express_repo(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {}, "engines": {"node": "20.x"}}), encoding="utf-8"
    )
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    (tmp_path / "index.js").write_text(
        "const port = process.env.PORT;\napp.listen(3000, () => {});",
        encoding="utf-8",
    )
    (tmp_path / ".env.example").write_text("PORT=3000\nDATABASE_URL=postgres://localhost/db\n", encoding="utf-8")

    result = analyze(tmp_path)

    assert result.stack[0].value == "node"
    assert result.package_manager.value == "npm"
    assert result.package_manager.confidence == Confidence.HIGH
    assert result.runtime_version.value == "20.x"
    assert any(d.value == "3000" for d in result.ports)
    assert any(d.value == "PORT" for d in result.env_vars)
    assert any(d.value == "postgres" for d in result.services)


def test_analyze_on_empty_repo_degrades_everything_to_low(tmp_path):
    result = analyze(tmp_path)

    assert all(d.confidence == Confidence.LOW for d in result.stack)
    assert result.package_manager.confidence == Confidence.LOW
    assert result.framework.confidence == Confidence.LOW
    assert result.runtime_version.confidence == Confidence.LOW
    assert all(d.value is None for d in result.ports)
    assert all(d.value is None for d in result.env_vars)
    assert all(d.value is None for d in result.services)


def test_analyze_excludes_node_modules_from_port_scan(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    node_modules = tmp_path / "node_modules" / "some-lib"
    node_modules.mkdir(parents=True)
    (node_modules / "server.js").write_text("app.listen(9999)", encoding="utf-8")

    result = analyze(tmp_path)

    assert all(d.value != "9999" for d in result.ports)
