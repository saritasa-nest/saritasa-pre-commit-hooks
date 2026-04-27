#!/usr/bin/env python3

import argparse
import pathlib
import re
import sys

# Error message printed for every found unreplaced placeholder
FOUND_PLACEHOLDER_MSG = "{filename}:{line}:{column}: unreplaced placeholder {placeholder}"

# Default name of the dotenv file containing placeholder variable names
DEFAULT_PLACEHOLDER_FILE = ".placeholders"


def parse_args(argv=None):
    """Parse CLI arguments.

    Args:
      argv: optional list of command-line arguments (default: sys.argv)

    Returns:
      argparse.Namespace object: parsed arguments including commit_filenames and mode

    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "commit_filenames",
        nargs="*",
        help="Files passed by pre-commit.",
    )
    parser.add_argument(
        "--regex",
        dest="regex_templates",
        action="append",
        required=True,
        help=(
            "Regex used for placeholder detection. Use {variables} as a placeholder. "
            "Can be passed multiple times."
        ),
    )
    parser.add_argument(
        "--file", "-f",
        dest="variables_file",
        default=DEFAULT_PLACEHOLDER_FILE,
        help=(
            "Path to the file containing placeholder variables. "
            "Empty lines, and lines starting with `#` will be ignored. "
        ),
    )

    return parser.parse_args(argv)


def load_variables(variables_file: str) -> list[str]:
    """Load placeholder variable names from the file.

    Args:
      variables_file: path to the file with placeholder variable names

    Returns:
      list[str]: list of configured placeholder variable names

    """
    config_path = pathlib.Path(variables_file)

    if not config_path.exists():
        raise ValueError(f"Config file does not exist: {variables_file}")

    with config_path.open(encoding="utf-8") as config_file:
        variables = [
            line.strip()
            for line in config_file
            if line.strip() and not line.lstrip().startswith("#")
        ]

    return variables


def get_patterns(variables: list[str], regex_templates: list[str]) -> list[str]:
    """Build patterns from the passed regex templates.

    Args:
      variables: list of placeholder variable names from the variables file, e.g `DOMAIN`
      regex_templates: regex templates passed through pre-commit arguments

    Returns:
      regexes: list of compiled placeholder regex patterns

    """
    if not variables:
        return []

    # Escape the variable name for symbols like "-", e.g. in `HELM_ARGO-CD`
    # And sort by longest variable first (`PROJECT_NAME` matched before `PROJECT`)
    escaped = sorted((re.escape(var) for var in variables), key=len, reverse=True)

    variables_regex = "|".join(escaped)

    regexes = []
    for template in regex_templates:
        if "{variables}" not in template:
            raise ValueError(f"Invalid regex {template!r}: missing the {{variables}} token")

        regexes.append(re.compile(template.format(variables=variables_regex)))

    return regexes


def find_placeholder_match(filename: str, regexes: list[str]) -> tuple(str, int, int):
    """Iterate over file contents and return placeholder matches found in it.

    Args:
      filename: name of the file passed by pre-commit
      regexes: placeholder names allowed for the passed regex style

    Returns:
      tuple: tuples of matched_placeholder, line_number, column_number

    """
    path = pathlib.Path(filename)

    try:
        # Open the file as UTF-8
        with path.open(encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                for regex in regexes:
                    for match in regex.finditer(raw_line):
                        yield match.group(0), line_number, match.start(0) + 1

    # Skip binary files
    except (UnicodeDecodeError, OSError):
        return


def check_files(filenames: list[str], variables_file: str, regex_templates: list[str]) -> int:
    """Check files for unreplaced placeholders.

    Args:
      filenames: names of the files passed by pre-commit
      variables_file: path to the file containing placeholder variable names
      regex_templates: regex templates to detect placeholders

    Returns:
      (int): 0 if check passes (no unreplaces placeholders found), 1 otherwise

    """
    # Load placeholder variables from the placeholder file once
    variables = load_variables(variables_file)
    regexes = get_patterns(variables, regex_templates)
    # Variable for file failures to show all errors in all files in one run
    has_errors = False

    for filename in filenames:
        for placeholder, line, column in find_placeholder_match(filename, regexes):
            has_errors = True
            print(FOUND_PLACEHOLDER_MSG.format(filename=filename, line=line, column=column, placeholder=placeholder))

    return 1 if has_errors else 0


def main(argv=None) -> int:
    """Parse CLI args and run placeholder validation.

    Args:
      argv: command-line args

    Returns:
      (int): 0 if check passes, 1 if placeholders are found, 2 for configuration errors

    """
    args = parse_args(argv)

    try:
        return check_files(
            filenames=args.commit_filenames,
            variables_file=args.variables_file,
            regex_templates=args.regex_templates,
        )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    # Exit the script with the returned status code
    sys.exit(main())
