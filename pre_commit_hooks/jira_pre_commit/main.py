#!/usr/bin/env python3

import argparse
import io
import re
import sys

from pre_commit_hooks.util import GIT_COMMENT_STRING, strip_comment_section

# Error message printed when no JIRA Task ID is found
NO_TASK_ERROR_MSG = "[ERROR] Aborting commit. Your commit message is missing a Jira Task ID, i.e. JIRA-1234."
# Error message when the regex is inavlid
INVALID_REGEX_ERROR_MSG = "[ERROR] Invalid regex '{pattern}': {error}"
# Message about excluded commit messsage
EXCLUDED_COMMIT_MSG = "Commit matches exclude pattern '{pattern}', skipping JIRA check."
# Regex pattern to match a JIRA Task ID (e.g. SD-373)
JIRA_TASK_REGEX = re.compile(r"[A-Z][A-Z0-9]+-\d+")


def parse_args(argv=None):
    """Parse CLI arguments for jira-pre-commit hook.

    Args:
      argv: optional list of command-line arguments (default: sys.argv)

    Returns:
      argparse.Namespace object: parsed arguments including commit_filename and exclude_pattern

    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "commit_filename",
        nargs=1,
        help="Path to `COMMIT_EDITMSG` file.",
    )
    parser.add_argument(
        "--exclude-pattern", "-e",
        action="append",
        help=(
            "Regex to exclude commit messages from Jira Task ID check. "
            "Can be specified multiple times."
        ),
    )

    return parser.parse_args(argv)


def is_commit_excluded(commit_message: str, patterns: list[str]) -> bool:
    """Check if commit message should be excluded from the Jira Task ID check.

    Args:
        commit_message: commit message text
        patterns: list of regex patterns to check commit message against

    Returns:
        (bool): whether commit message matches the exclusion pattern

    """
    for pattern in patterns:
        try:
            if re.search(pattern, commit_message):
                print(EXCLUDED_COMMIT_MSG.format(pattern=pattern))
                return True
        except re.PatternError as e:
            print(INVALID_REGEX_ERROR_MSG.format(pattern=pattern, error=e))
            sys.exit(1)
    return False


def validate_task_in_commit(commit_filename: str, exclude_patterns: list) -> int:
    """Check commit message for Jira Task ID, unless it matches an exclusion pattern.

    Args:
        commit_filename: path to the `COMMIT_EDITMSG` file
        exclude_patterns: list of regex patterns to check commit message against

    Returns:
        (int): 0 if validation passes or skipped, 1 if validation fails

    """
    with io.open(commit_filename, "r") as commit_message_file:
        commit_message = commit_message_file.read()
        commit_message = strip_comment_section(commit_message)
        commit_message = commit_message.strip()

    # Strip commit message from comment lines (usually added by `git rebase` or `git commit --amend`)
    # To avoid false positives (i.e. there could be a Jira ID in the comments, but not in the actual commit message)
    lines = commit_message.splitlines()
    non_comment_lines = [line for line in lines if not line.startswith(GIT_COMMENT_STRING)]
    commit_message = "\n".join(non_comment_lines)

    # If any exclusion pattern matches, skip Jira checks
    if exclude_patterns and is_commit_excluded(commit_message, exclude_patterns):
        return 0

    if not re.search(JIRA_TASK_REGEX, commit_message):
        print(NO_TASK_ERROR_MSG)
        return 1

    # If commit message has a Jira Task ID
    return 0


def main(argv=None) -> int:
    """Parse CLI args and run Jira Task ID validation on the commit message.

    Args:
        argv: command-line args

    Returns:
        (int): 0 if validation passes or excluded, 1 otherwise

    """
    args = parse_args(argv)
    return validate_task_in_commit(args.commit_filename[0], args.exclude_pattern)


if __name__ == "__main__":
    # Exit the script with the returned status code
    sys.exit(main())
