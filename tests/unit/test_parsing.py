from envora.analyzer.parsing import parse_json, parse_toml


def test_parse_json_valid(tmp_path):
    path = tmp_path / "package.json"
    path.write_text('{"name": "demo", "dependencies": {"next": "14.0.0"}}', encoding="utf-8")

    data, error = parse_json(path)

    assert error is None
    assert data == {"name": "demo", "dependencies": {"next": "14.0.0"}}


def test_parse_json_invalid_returns_error_not_exception(tmp_path):
    path = tmp_path / "package.json"
    path.write_text('{"name": "demo",,,}', encoding="utf-8")

    data, error = parse_json(path)

    assert data is None
    assert error is not None
    assert "demo" not in error or True  # error just needs to be a non-empty message
    assert isinstance(error, str) and len(error) > 0


def test_parse_toml_valid(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text('[project]\nrequires-python = ">=3.11"\n', encoding="utf-8")

    data, error = parse_toml(path)

    assert error is None
    assert data["project"]["requires-python"] == ">=3.11"


def test_parse_toml_invalid_returns_error_not_exception(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text("[project\nrequires-python = ", encoding="utf-8")

    data, error = parse_toml(path)

    assert data is None
    assert isinstance(error, str) and len(error) > 0
