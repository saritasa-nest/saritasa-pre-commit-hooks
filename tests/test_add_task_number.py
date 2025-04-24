import pytest

from pre_commit_hooks import util as base_util
from pre_commit_hooks.add_task_number import main


@pytest.fixture
def branch_regex() -> str:
    """Return default branch regex to test the hook."""
    return "^feature/(?P<task>[A-Z0-9]+-[0-9]+)-.*$"


@pytest.fixture
def format_template() -> str:
    """Return default format template to test the hook."""
    return "{message}\n\nTask: {task}"


def test_is_task_in_message():
    """Test `is_task_in_message` util function."""
    commit_msg = (
        "My beautiful commit message\n\n"
        "My beautiful description of commit.\n\n"
        "Task: ABC-1234\n"
    )

    assert main.is_task_in_message(commit_msg, "Task: ABC-1234") is True
    assert main.is_task_in_message(commit_msg, "Task: abc-1234") is True

    assert main.is_task_in_message(commit_msg, "Task: ABC-123") is False
    assert main.is_task_in_message(commit_msg, "Task: abc-123") is False

    assert main.is_task_in_message(commit_msg, "Task: BC-1234") is False
    assert main.is_task_in_message(commit_msg, "Task: bc-1234") is False

    assert main.is_task_in_message(commit_msg, "Task: CDE-111") is False


def test_get_message_without_comment_section():
    """Test that comment section will be cut off by this util function."""
    commit_msg = (
        "My beautiful commit message\n\n"
        "My beautiful description of commit.\n\n"
        "--- >8 ---\n\n"
        "My beautiful comment section."
    )
    expected_commit_msg = (
        "My beautiful commit message\n\n"
        "My beautiful description of commit."
    )

    msg_without_comment_section = main.strip_comment_section(
        commit_msg,
    )

    assert msg_without_comment_section.strip() == expected_commit_msg.strip()


def test_add_task_number(
    temp_git_dir,
    branch_regex,
    format_template,
):
    """Test pre-commit hook itself."""
    with temp_git_dir.as_cwd():
        # Need to make init commit before creation of branch to avoid errors
        base_util.git_commit("Init commit")
        base_util.git_create_branch("feature/ABC-123-my-beautiful-branch")
        base_util.git_commit("My beautiful commit message")

        expected_commit_message = (
            "My beautiful commit message\n\n"
            "Task: ABC-123"
        )

        commit_msg_file_path = f"{temp_git_dir}/.git/COMMIT_EDITMSG"

        main.add_task_number(
            filename=commit_msg_file_path,
            branch_regex=branch_regex,
            format_template=format_template,
        )
        with open(commit_msg_file_path, "r") as commit_msg_file:
            last_commit_message = commit_msg_file.read()

        assert last_commit_message == expected_commit_message


def test_empty_commit_message_will_not_be_modified(
    temp_git_dir,
    branch_regex,
    format_template,
):
    """Test that empty commit message will remain empty."""
    with temp_git_dir.as_cwd():
        # Need to make init commit before creation of branch to avoid errors
        base_util.git_commit("Init commit")
        base_util.git_create_branch("feature/ABC-123-my-beautiful-branch")

        expected_commit_message = ""

        commit_msg_file_path = f"{temp_git_dir}/.git/COMMIT_EDITMSG"
        # Remove everything from the file
        with open(commit_msg_file_path, "w"):
            pass

        main.add_task_number(
            filename=commit_msg_file_path,
            branch_regex=branch_regex,
            format_template=format_template,
        )
        with open(commit_msg_file_path, "r") as commit_msg_file:
            last_commit_message = commit_msg_file.read()

        assert last_commit_message == expected_commit_message


def test_commit_message_will_not_be_modified_for_wrong_branch(
    temp_git_dir,
    branch_regex,
    format_template,
):
    """Test that commit message will not be modified on wrong branch.

    Check that if task is not presented in branch name, then no info will be
    appended to the commit message.

    """
    with temp_git_dir.as_cwd():
        # Need to make init commit before creation of branch to avoid errors
        base_util.git_commit("Init commit")
        base_util.git_create_branch("feature/no-task-number-in-branch")

        expected_commit_message = "Init commit\n"

        commit_msg_file_path = f"{temp_git_dir}/.git/COMMIT_EDITMSG"

        main.add_task_number(
            filename=commit_msg_file_path,
            branch_regex=branch_regex,
            format_template=format_template,
        )
        with open(commit_msg_file_path, "r") as commit_msg_file:
            last_commit_message = commit_msg_file.read()

        assert last_commit_message == expected_commit_message
