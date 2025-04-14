#!/usr/bin/env python

import argparse

from .util import add_task_number


def parse_args(argv=None):
    """Provide CLI for the tool."""
    parser = argparse.ArgumentParser(
        description="Script that adds task number to each commit",
    )

    parser.add_argument("filenames", nargs="+")
    parser.add_argument(
        "--branch-regex",
        default=r"(feature|fix)/(?P<task>[A-Z0-9]+-[0-9]+)-.*",
        type=str,
    )
    parser.add_argument(
        "--format",
        default="{message}\\n\\nTask: {task}",
        type=str,
    )

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    format_template = (
        args.format
        .encode("utf-8")
        .decode("unicode_escape")  # argparse escapes backslash by default
    )

    add_task_number(args.filenames[0], args.branch_regex, format_template)


if __name__ == "__main__":
    SystemExit(main())
