from envora.analyzer.walk import MAX_SCAN_FILE_BYTES, read_text_safe, walk_repo


def test_walk_repo_finds_files(tmp_path):
    (tmp_path / "app.py").write_text("print('hi')", encoding="utf-8")
    nested = tmp_path / "src"
    nested.mkdir()
    (nested / "main.py").write_text("print('hi')", encoding="utf-8")

    files = walk_repo(tmp_path)

    names = {f.name for f in files}
    assert "app.py" in names
    assert "main.py" in names


def test_walk_repo_excludes_node_modules_and_friends(tmp_path):
    for excluded_dir in ("node_modules", ".git", "dist", "build", "venv", ".venv", "__pycache__", ".next", "target", "vendor"):
        d = tmp_path / excluded_dir
        d.mkdir()
        (d / "should_not_appear.txt").write_text("x", encoding="utf-8")
    (tmp_path / "real_file.py").write_text("print('hi')", encoding="utf-8")

    files = walk_repo(tmp_path)

    names = {f.name for f in files}
    assert "should_not_appear.txt" not in names
    assert "real_file.py" in names


def test_read_text_safe_returns_content_for_normal_file(tmp_path):
    path = tmp_path / "readme.txt"
    path.write_text("hello world", encoding="utf-8")

    assert read_text_safe(path) == "hello world"


def test_read_text_safe_returns_none_for_oversized_file(tmp_path):
    path = tmp_path / "big.txt"
    path.write_bytes(b"x" * (MAX_SCAN_FILE_BYTES + 1))

    assert read_text_safe(path) is None


def test_read_text_safe_returns_none_for_missing_file(tmp_path):
    assert read_text_safe(tmp_path / "does_not_exist.txt") is None
