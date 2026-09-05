import shutil

import git
import pytest

from envora.cloner import ClonedRepo, CloneError, clone


@pytest.fixture
def local_source_repo(tmp_path):
    source = tmp_path / "source_repo"
    source.mkdir()
    repo = git.Repo.init(source, initial_branch="main")
    (source / "README.md").write_text("hello", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("initial commit")
    return source


def test_clone_succeeds_and_returns_path_and_branch(local_source_repo):
    with clone(str(local_source_repo)) as cloned:
        assert cloned.path.is_dir()
        assert (cloned.path / "README.md").is_file()
        assert cloned.branch == "main"
        assert cloned.url == str(local_source_repo)
        temp_dir = cloned.path

    assert not temp_dir.exists()  # context manager cleans up on exit


def test_exit_never_propagates_cleanup_failure(tmp_path, monkeypatch):
    def always_fails(*args, **kwargs):
        raise OSError("directory is busy")

    monkeypatch.setattr(shutil, "rmtree", always_fails)
    cloned = ClonedRepo(path=tmp_path, branch="main", url="file:///somewhere")

    with pytest.warns(RuntimeWarning, match="could not remove temporary clone"):
        with cloned:
            pass  # a successful analysis must not be lost to a cleanup error


def test_clone_raises_clone_error_for_nonexistent_source(tmp_path):
    bad_path = tmp_path / "does_not_exist"

    with pytest.raises(CloneError) as exc_info:
        clone(str(bad_path))

    assert exc_info.value.url == str(bad_path)
    assert exc_info.value.cause is not None
