#!/usr/bin/env python3

import argparse
import pathlib
import re
import sys
import tomllib

# Error message printed for every found unreplaced placeholder
FOUND_PLACEHOLDER_MSG = "{filename}:{line}:{column}: unreplaced placeholder {placeholder}"
# Supported detection modes
MODE_KUBERNETES = "kubernetes"   # `$VAR`
MODE_TERRAFORM = "terraform"     # `__VAR__`
MODE_BOTH = "both"               # matches both styles
VALID_MODES = (MODE_KUBERNETES, MODE_TERRAFORM, MODE_BOTH)


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
        "--mode", "-m",
        choices=VALID_MODES,
        default=MODE_BOTH,
        help=(
            "Mode to check for placeholders in a certain pattern. By default uses `both` mode. "
            "`kubernetes` checks `$VAR`, `terraform` checks `__VAR__`, `both` checks both styles."
        ),
    )

    return parser.parse_args(argv)


def load_variables() -> list[str]:
    """Load placeholder variables from the placeholders.toml file.

    Args:
      none

    Returns:
      list[str]: list of configured placeholder variables

    """
    config_path = pathlib.Path(__file__).parent.resolve() / "placeholders.toml"
    with open(config_path, "rb") as config_file:
        variables = tomllib.load(config_file).get("variables", [])

    return variables


def get_patterns(variable: str, mode: str) -> list[str]:
    """Build regex patterns for a variable based on the selected mode.

    Args:
      variable: placeholder from the placeholders.toml file, e.g. `DOMAIN`
      mode: selected matching mode, e.g. `kubernetes` or `terraform`

    Returns:
      list[str]: list of compiled regex patterns for the requested mode

    """
    # Escape the variable name for symbols like "-", e.g. in `HELM_ARGO-CD`
    escaped = re.escape(variable)
    patterns = []

    # Get patterns for variables of the `$VAR` type
    if mode in (MODE_KUBERNETES, MODE_BOTH):
        patterns.append(
            re.compile(rf"(\${escaped})"),
        )

    # Get patterns for variables of the `__VAR__` type
    if mode in (MODE_TERRAFORM, MODE_BOTH):
        patterns.append(
            re.compile(rf"(__{escaped}__)"),
        )

    return patterns


def find_placeholder_match(filename: str, variables: list[str], mode: str) -> tuple(str, int, int):
    """Iterate over file contents and return placeholder matches found in it.

    Args:
      filename: name of the file passed by pre-commit
      variables: list of placeholder variables from placeholders.toml
      mode: mode passed by pre-commit to check

    Returns:
      tuple: (matched_placeholder, line_number, column_number)

    """
    path = pathlib.Path(filename)

    try:
        # Open the file as UTF-8
        with path.open(encoding="utf-8") as handle:
            # Read the file line by line, get line number and the whole line
            for line_number, raw_line in enumerate(handle, start=1):
                line_text = raw_line.strip()
                # Go through every configured placeholder
                for variable in variables:
                    # Build patterns for this placeholder, depending on the passed mode
                    for pattern in get_patterns(variable, mode):
                        # Find all matches of this pattern in the current line
                        for match in pattern.finditer(line_text):
                            matched_placeholder = match.group(1)
                            column_number = match.start(1) + 1

                            yield (matched_placeholder, line_number, column_number)
    # Skip binary files
    except (UnicodeDecodeError, OSError):
        return


def check_files(filenames: list[str], mode: str) -> int:
    """Check files for unreplaced placeholders.

    Args:
      filenames: name of the files passed by pre-commit
      mode: mode passed by pre-commit to check

    Returns:
      (int): 0 if check passes (no unreplaces placeholders found), 1 otherwise

    """
    # Load placeholder variables from the `placeholders.toml` file once
    variables = load_variables()
    # Variable for file failures to show all errors in all files in one run
    has_errors = False

    for filename in filenames:
        # Get all matches from one file in a list of tuples
        matches = list(find_placeholder_match(filename, variables, mode))
        if not matches:
            continue

        has_errors = True

        # Go through all match tuples from the file
        for placeholder, line, column in matches:
            print(FOUND_PLACEHOLDER_MSG.format(filename=filename, line=line, column=column, placeholder=placeholder))

    return 1 if has_errors else 0


def main(argv=None) -> int:
    """Parse CLI args and run placeholder validation.

    Args:
      argv: command-line args

    Returns:
      (int): 0 if check passes, 1 otherwise

    """
    args = parse_args(argv)
    return check_files(args.commit_filenames, args.mode)


if __name__ == "__main__":
    # Exit the script with the returned status code
    sys.exit(main())
