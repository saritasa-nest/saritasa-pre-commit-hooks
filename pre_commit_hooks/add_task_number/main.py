import io
import re

from pre_commit_hooks.util import get_current_branch, get_git_config_param

GIT_COMMENT_STRING = (
    get_git_config_param("core.commentString")
    or get_git_config_param("core.commentChar")
    or "#"
)
GIT_COMMENT_SECTION_LINE = (
    r"{comment_string}?[ ]*-+ >8 -+".format(comment_string=GIT_COMMENT_STRING)
)


def retrieve_task(branch: str, branch_regex: str) -> str | None:
    """Retrieve task from branch according to the given regex."""
    matches = re.match(branch_regex, branch)

    if not matches:
        return

    task_number = matches.group("task")
    return task_number


def is_task_in_message(contents: str, task: str) -> bool:
    """Check whether task has been already added to commit message."""
    task_regex = r"\b{task}\b".format(task=task)

    for line in contents.splitlines():
        stripped = line.strip()

        # Skip empty lines and comment lines
        if stripped == "" or stripped.startswith(GIT_COMMENT_STRING):
            continue

        if re.search(task_regex, contents, re.IGNORECASE):
            return True

    return False


def strip_comment_section(message: str) -> str:
    """Return message without comment section which is located bellow the line.

    All bellow this line will be ignored including task number. So need to
    strip it to avoid appending of task number bellow this line.

    Example:
    ```
    My beautiful commit message

    ------------------------ >8 ------------------------

    This is considered a comment section by git, so everything bellow the line
    will be ignored. We need to cut if off before appending task number,
    because otherwise task number will be appended bellow this line and, thus,
    it will be cut off.

    ```

    """
    match = re.search(GIT_COMMENT_SECTION_LINE, message)

    if match is not None:
        return message[:match.start()]

    return message


def add_task_number(filename: str, branch_regex: str, format_template: str):
    """Provide task number to commit message."""
    branch = get_current_branch()
    task_number = retrieve_task(branch, branch_regex)

    if not task_number:
        return

    with io.open(filename, "r+") as commit_message_file:
        commit_message = commit_message_file.read()
        commit_message = strip_comment_section(
            commit_message,
        )
        commit_message = commit_message.strip()

        is_empty_message = not commit_message

        formatted_task_number = format_template.format(
            message="",
            task=task_number,
        ).strip()

        skip_task_appending = (
            is_task_in_message(commit_message, formatted_task_number)
            or is_empty_message
        )

        if skip_task_appending:
            return

        commit_message_with_task = format_template.format(
            message=commit_message,
            task=task_number,
        )

        commit_message_file.seek(0)
        commit_message_file.write(commit_message_with_task)
        commit_message_file.truncate()

    print(f"Message `{formatted_task_number}` was appended to your commit.")
