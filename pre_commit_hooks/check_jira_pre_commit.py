#!/usr/bin/env python3

import argparse
import io
import re
import sys

COMMIT_REGEX = re.compile(r"[A-Z]+-[0-9]+")
ERROR_MSG = "Aborting commit. Your commit message is missing a Jira Task ID, i.e. JIRA-1234."


def parse_args(argv=None):
    """Check commit message for Jira Task ID."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="+",
        help="Path to `COMMIT_EDITMSG` file.",
    )

    return parser.parse_args(argv)


def check_commit(path: str):
    with io.open(path, "r+") as commit_message_file:
        commit_text = commit_message_file.read()

    if commit_text.startswith("Merge "):
        print("Ignoring git merge commit")
        sys.exit(0)

    match = re.search(COMMIT_REGEX, commit_text)
    if not match:
        print(ERROR_MSG)
        sys.exit(1)


def main(argv=None):
    args = parse_args(argv)
    check_commit(args.path[0])


if __name__ == "__main__":
    SystemExit(main())
