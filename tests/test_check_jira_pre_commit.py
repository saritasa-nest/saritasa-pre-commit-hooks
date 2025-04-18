import pytest

from pre_commit_hooks.check_jira_pre_commit import ERROR_MSG, check_commit


def test_invalid_commit_message(tmp_path, capsys):
    """Test that a commit message without a JIRA ID fails and prints the expected error message."""
    path = tmp_path / "COMMIT_EDITMSG"
    path.write_text("feat: update login")

    with pytest.raises(SystemExit) as e:
        check_commit(str(path))
    assert e.value.code == 1

    out, _ = capsys.readouterr()
    assert ERROR_MSG in out


def test_valid_commit_message(tmp_path, capsys):
    """Test that a commit message with a valid JIRA ID passes."""
    path = tmp_path / "COMMIT_EDITMSG"
    path.write_text("feat: add config JIRA-1234")

    check_commit(str(path))

    out, _ = capsys.readouterr()
    assert out == ""


def test_merge_commit_message(tmp_path, capsys):
    """Test that a merge commit is detected and skipped."""
    path = tmp_path / "COMMIT_EDITMSG"
    path.write_text("Merge remote-tracking branch 'feature/test' into 'main'")

    with pytest.raises(SystemExit) as e:
        check_commit(str(path))
    assert e.value.code == 0

    out, _ = capsys.readouterr()
    assert "Ignoring git merge commit" in out
