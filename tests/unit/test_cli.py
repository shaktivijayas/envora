import json

from typer.testing import CliRunner

import envora.cli as cli_module
from envora.cli import app
from envora.cloner import ClonedRepo, CloneError

runner = CliRunner()


def test_analyze_command_prints_json_result(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text('{"dependencies": {}}', encoding="utf-8")

    def fake_clone(url: str) -> ClonedRepo:
        return ClonedRepo(path=tmp_path, branch="main", url=url)

    monkeypatch.setattr(cli_module, "clone", fake_clone)

    result = runner.invoke(app, ["https://github.com/example/repo"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["stack"][0]["value"] == "node"


def test_analyze_command_reports_clone_error_cleanly(monkeypatch):
    def fake_clone(url: str) -> ClonedRepo:
        raise CloneError(url, RuntimeError("network unreachable"))

    monkeypatch.setattr(cli_module, "clone", fake_clone)

    result = runner.invoke(app, ["https://github.com/example/does-not-exist"])

    assert result.exit_code == 1
    assert "Error" in result.output
    assert "Traceback" not in result.output
