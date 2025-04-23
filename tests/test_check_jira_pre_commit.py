import pytest

from pre_commit_hooks.jira_pre_commit.main import ERROR_MSG, validate_task_in_commit


@pytest.fixture
def commit_msg_file(tmp_path):
    def create_commit_msg(text):
        path = tmp_path / "COMMIT_EDITMSG"
        path.write_text(text, newline='\n')
        return str(path)
    return create_commit_msg


def test_no_task_in_commit_message(commit_msg_file, capsys):
    """Test that a commit message without a JIRA ID fails and prints the expected error message."""
    path = commit_msg_file("feat: update login")

    exit_code = validate_task_in_commit(path, [])
    assert exit_code == 1

    out, _ = capsys.readouterr()
    assert ERROR_MSG in out


def test_invalid_commit_message(commit_msg_file, capsys):
    """Test that a commit message with an invalid JIRA ID fails and prints the expected error message."""
    path = commit_msg_file("feat: update login jira1234")

    exit_code = validate_task_in_commit(path, [])
    assert exit_code == 1

    out, _ = capsys.readouterr()
    assert ERROR_MSG in out


def test_task_in_commit_message(commit_msg_file, capsys):
    """Test that a commit message with a valid JIRA ID passes."""
    path = commit_msg_file("feat: add config JIRA-1234")

    exit_code = validate_task_in_commit(path, [])
    assert exit_code == 0

    out, _ = capsys.readouterr()
    assert out == ""


def test_multiline_commit_message(commit_msg_file, capsys):
    """Test that a commit message with a valid multi-line JIRA ID passes."""
    path = commit_msg_file("feat: add config\nTask: JIRA-1234")

    exit_code = validate_task_in_commit(path, [])
    assert exit_code == 0

    out, _ = capsys.readouterr()
    assert out == ""


def test_exclude_commit_message(commit_msg_file, capsys):
    """Test that a commit message is excluded if it matches the exclude pattern."""
    path = commit_msg_file("Merge remote-tracking branch 'feature/test' into 'main'")

    exit_code = validate_task_in_commit(path, ['^Merge '])
    assert exit_code == 0

    out, _ = capsys.readouterr()
    assert "Commit matches exclude pattern '^Merge ', skipping JIRA check." in out


def test_exclude_pattern_error(commit_msg_file, capsys):
    """Test that an invalid regex pattern causes the script to exit with error."""
    path = commit_msg_file("feat: valid commit JIRA-1234")

    with pytest.raises(SystemExit) as e:
        validate_task_in_commit(path, ['(unclosed'])
    assert e.value.code == 1

    out, _ = capsys.readouterr()
    assert "[ERROR] Invalid regex '(unclosed':" in out
