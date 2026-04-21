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


def get_patterns(variables: list[str], mode: str) -> tuple(set[str], set[str]):
    """Build sets for lookup based on the selected mode.

    Args:
      variable: placeholder from the placeholders.toml file, e.g. `DOMAIN`
      mode: selected matching mode, e.g. `kubernetes` or `terraform`

    Returns:
      tuple: tuple of two sets - kubernetes and terraform placeholder names

    """
    # Escape the variable name for symbols like "-", e.g. in `HELM_ARGO-CD`
    # And sort by longest variable first (`PROJECT_NAME` matched before `PROJECT`)
    escaped = sorted((re.escape(var) for var in variables), key=len, reverse=True)

    kubernetes_regex = None
    terraform_regex = None

    # Get patterns for variables of the `$VAR` type
    if mode in (MODE_KUBERNETES, MODE_BOTH):
        kubernetes_regex = re.compile(rf"\$({'|'.join(escaped)})")

    # Get patterns for variables of the `__VAR__` type
    if mode in (MODE_TERRAFORM, MODE_BOTH):
        terraform_regex = re.compile(rf"__({'|'.join(escaped)})__")

    return kubernetes_regex, terraform_regex


def find_placeholder_match(
    filename: str,
    kubernetes_regex: set[str],
    terraform_regex: set[str],
    mode: str,
) -> tuple(str, int, int):
    """Iterate over file contents and return placeholder matches found in it.

    Args:
      filename: name of the file passed by pre-commit
      kubernetes_regex: placeholder names allowed for kubernetes-style
      terraform_regex: placeholder names allowed for terraform-style
      mode: mode passed by pre-commit to check

    Returns:
      tuple: tuples of matched_placeholder, line_number, column_number

    """
    path = pathlib.Path(filename)

    try:
        # Open the file as UTF-8
        with path.open(encoding="utf-8") as handle:
            # Read the file line by line, get line number and the whole line
            for line_number, raw_line in enumerate(handle, start=1):
                # Scan for kubernetes-style placeholders ($VAR)
                if mode in (MODE_KUBERNETES, MODE_BOTH) and kubernetes_regex:
                    for match in kubernetes_regex.finditer(raw_line):
                        yield match.group(0), line_number, match.start(0) + 1
                # Scan for terraform-style placeholders (__VAR__)
                if mode in (MODE_TERRAFORM, MODE_BOTH) and terraform_regex:
                    for match in terraform_regex.finditer(raw_line):
                        yield match.group(0), line_number, match.start(0) + 1
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
    kubernetes_regex, terraform_regex = get_patterns(variables, mode)
    # Variable for file failures to show all errors in all files in one run
    has_errors = False

    for filename in filenames:
        for placeholder, line, column in find_placeholder_match(filename, kubernetes_regex, terraform_regex, mode):
            has_errors = True
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
