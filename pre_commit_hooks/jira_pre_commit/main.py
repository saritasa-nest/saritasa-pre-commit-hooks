#!/usr/bin/env python3

import argparse
import io
import re
import sys

# Regex pattern to match a JIRA Task ID (e.g. SD-373)
GIT_COMMIT_REGEX = re.compile(r"(?<![A-Z])[A-Z]{2,11}(?![A-Z])-(?<![0-9])[0-9]{1,6}(?![0-9])")
# Error message printed when no JIRA Task ID is found
ERROR_MSG = "[ERROR] Aborting commit. Your commit message is missing a Jira Task ID, i.e. JIRA-1234."


def parse_args(argv=None):
    """Provide CLI for jira_pre_commit hook."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filename",
        nargs=1,
        help="Path to `COMMIT_EDITMSG` file.",
    )
    parser.add_argument(
        "--exclude-pattern", "-e",
        action="append",
        default=['^Merge '],
        help=(
            "Regex to exclude commit messages from Jira Task ID check. "
            "Can be specified multiple times. Default is '^Merge '."
        ),
    )

    return parser.parse_args(argv)


def check_exclusions(commit_message: str, patterns: list) -> int:
    """
    Check if commit message should be excluded from the Jira Task ID check.

    Args:
        commit_message: commit message text
        patterns: list of regex patterns to check commit message against

    Returns:
        (int): whether commit message matches the exclusion pattern
    """
    for pattern in patterns:
        try:
            if re.search(pattern, commit_message):
                print(f"Commit matches exclude pattern '{pattern}', skipping JIRA check.")
                return 1
        except re.PatternError as e:
            print(f"[ERROR] Invalid regex '{pattern}': {e}")
            sys.exit(1)
    return 0


def validate_task_in_commit(filename: str, exclude_patterns: list) -> int:
    """
    Check commit message for Jira Task ID, unless it matches an exclusion pattern.

    Args:
        filename: path to the `COMMIT_EDITMSG` file
        exclude_patterns: list of regex patterns to check commit message against

    Returns:
        (int): 0 if validation passes or skipped, 1 if validation fails
    """
    with io.open(filename, "r") as commit_message_file:
        commit_message = commit_message_file.read()

    # Strip commit message from comment lines (usually added by `git rebase` or `git commit --amend`)
    # To avoid false positives (i.e. there could be a Jira ID in the comments, but not in the actual commit message)
    lines = commit_message.splitlines()
    non_comment_lines = [line for line in lines if not line.startswith('#')]
    commit_message = "\n".join(non_comment_lines)

    # If any exclusion pattern matches, skip Jira checks
    if exclude_patterns and check_exclusions(commit_message, exclude_patterns):
        return 0

    match = re.search(GIT_COMMIT_REGEX, commit_message)
    if not match:
        print(ERROR_MSG)
        return 1

    # If commit message has a Jira Task ID
    return 0


def main(argv=None) -> int:
    """
    Parse CLI args and run Jira Task ID validation on the commit message. Exit with code 0 on success, 1 on failure.

    Args:
        argv: command-line args

    Returns:
        (int): exit code for the hook
    """
    args = parse_args(argv)
    return validate_task_in_commit(args.filename[0], args.exclude_pattern)


if __name__ == "__main__":
    # Exit the script with the returned status code
    sys.exit(main())
