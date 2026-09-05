from envora.analyzer.parsing import parse_json, parse_toml
from envora.analyzer.walk import MAX_SCAN_FILE_BYTES


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


def test_parse_json_oversized_file_is_skipped_not_read(tmp_path):
    path = tmp_path / "package.json"
    padding = " " * (MAX_SCAN_FILE_BYTES + 1)
    path.write_text("{}" + padding, encoding="utf-8")

    data, error = parse_json(path)

    assert data is None
    assert "size cap" in error


def test_parse_toml_oversized_file_is_skipped_not_read(tmp_path):
    path = tmp_path / "pyproject.toml"
    padding = "\n" * (MAX_SCAN_FILE_BYTES + 1)
    path.write_text("[project]" + padding, encoding="utf-8")

    data, error = parse_toml(path)

    assert data is None
    assert "size cap" in error


def test_parse_json_non_utf8_bytes_does_not_raise(tmp_path):
    path = tmp_path / "package.json"
    path.write_bytes(b'{"name": "caf\xe9"}')

    # Must not raise UnicodeDecodeError; a decode-replaced parse failure is fine.
    data, error = parse_json(path)

    assert data is None or isinstance(data, dict)
    if data is None:
        assert isinstance(error, str) and len(error) > 0


def test_parse_toml_non_utf8_bytes_does_not_raise(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_bytes(b'[project]\nname = "caf\xe9"\n')

    data, error = parse_toml(path)

    assert data is None or isinstance(data, dict)
    if data is None:
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
