import io
import re

from pre_commit_hooks.util import cmd_output

GIT_COMMENT_SECTION_LINE = r"#?[ ]*-+ >8 -+"


def get_current_branch() -> str:
    """Return current branch's name."""
    return cmd_output("git", "rev-parse", "--abbrev-ref", "HEAD")


def retrieve_task(branch: str, regex: str) -> str | None:
    """Retrieve task from branch according to the given regex."""
    matches = re.match(regex, branch)

    if not matches:
        return

    task_number = matches.group("task")
    return task_number


def is_task_in_message(contents: str, task: str) -> bool:
    """Check whether task has been already added to commit message."""
    for line in contents.splitlines():
        stripped = line.strip().lower()

        # Skip empty lines and comment lines
        if stripped == "" or stripped.startswith("#"):
            continue

        if task.lower() in stripped:
            return True

    return False


def get_message_without_comment_section(message: str) -> str:
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

    Also remove lines which start with `#` because they are considered to be
    comment lines.

    """
    match = re.search(GIT_COMMENT_SECTION_LINE, message)

    if match is not None:
        result_message = message[:match.start()]
    else:
        result_message = message

    return "\n".join(
        line
        for line in result_message.splitlines()
        if not line.startswith("#")
    )


def add_task_number(filename: str, regex: str, format_template: str):
    """Provide task number to commit message."""
    branch = get_current_branch()
    task_number = retrieve_task(branch, regex)

    if not task_number:
        return

    with io.open(filename, "r+") as commit_message_file:
        commit_message = commit_message_file.read()
        commit_message = get_message_without_comment_section(
            commit_message,
        )
        commit_message = commit_message.strip()

        is_empty_message = not commit_message

        skip_task_appending = (
            is_task_in_message(commit_message, task_number)
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
