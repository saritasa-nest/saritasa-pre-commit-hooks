import argparse
import re
from typing import Any, Dict, List, Sequence

import crossplane


def _search_directive(
    config: Dict,
    name: str,
    value: Any | None = None,
    results: List[Dict] | None = None,
) -> List[Dict]:
    """Search all entries of `name` directive in tree and add to `results`.

    If `value` is passed - search for directive with exact value.

    Args:
      config: dict with current nginx config content
      name: searched directive name
      value: if passed search for concrete directive `name` with exact `value`
      results: list with `search` results

    Returns:
      (list): list with found directives configs

    """
    results = results or []
    if config["directive"] == name:
        if value is None or config["args"] == value:
            results.append(config)

    blocks = config.get("block", [])
    for block in blocks:
        block["file"] = config.get("file")
        results = _search_directive(block, name, value, results)
    return results


def _disabled_locations_exist(locations: List[Dict] | None = None) -> bool:
    """Check that all corresponding `disabled` locations were added.

    Search for below directives in nginx config, if at least one of them
    is not defined - error will be raised:

        location ~ \.(json|sh|conf|xml|md|conf|toml|yml|yaml|log|pid)$  {deny all;}
        location ~ /cron.*                                              {deny all;}
        location ~ /\.                                                  {deny all;}
        location ~ autodiscover.xml {return 403;}
        location ~ apple-touch-icon {return 403;}
        location ~ ^/(app/|vendor|src|tests|vagrant|docs|phpunit|svn|git|docker|migrations|Makefile) {return 403;}

    Args:
      locations: list with all `locations` directives configs found in nginx config

    Returns:
      (bool): flag whether all required disabled `locations` directives are added

    """
    locations = locations or []

    # locations args that should exactly match
    exact_match = [
        dict(regex=r"^{item}$", values=[item[0]], expected=item[1], exists=False)
        for item in [
            ("/cron\.\*", "/cron.*"),
            ("/\\\.", "/\."),
            ("autodiscover\.xml", "autodiscover.xml"),
            ("apple-touch-icon", "apple-touch-icon"),
        ]
    ]

    # location args that may be not exactly matched, checked by regex
    regex_match = [
        dict(
            regex=r"^\\\.\(.*{item}.*\)\$$",
            values=[
                "json",
                "sh",
                "xml",
                "md",
                "conf",
                "toml",
                "yml",
                "yaml",
                "log",
                "pid",
            ],
            expected="\.(json|sh|xml|md|conf|toml|yml|yaml|log|pid)$",
            exists=False,
        ),
        dict(
            regex=r"^\^/\(.*{item}.*\)",
            values=[
                "app/",
                "vendor",
                "src",
                "tests",
                "vagrant",
                "docs",
                "phpunit",
                "svn",
                "git",
                "docker",
                "migrations",
                "Makefile",
            ],
            expected="^/(app/|vendor|src|tests|vagrant|docs|phpunit|svn|git|docker|migrations|Makefile)",
            exists=False,
        ),
    ]

    for location in locations:
        if location["args"][0] != "~":
            continue

        for item in exact_match + regex_match:
            # proceed for searching of `deny all;` and `return 403;` directives
            # only if `location` contains all values from `item["values"]`, otherwise
            # break loop and consider that not all `required` values were found
            all_values_found = True
            for value in item["values"]:
                if not re.match(item["regex"].format(item=value), location["args"][1]):
                    all_values_found = False
                    break

            if not all_values_found:
                continue

            deny = _search_directive(config=location, name="deny", value=["all"])
            return_403 = _search_directive(
                config=location,
                name="return",
                value=["403"],
            )

            if deny or return_403:
                item["exists"] = True

    all_disabled_locations_found = True
    for item in exact_match + regex_match:
        if item["exists"] != True:
            all_disabled_locations_found = False
            print(
                f"[ERROR] location not disabled: `location ~ {item['expected']}`. "
                "Please disable it with `{{deny all;}}` or `{{return 403;}}` directives.",
            )

    return all_disabled_locations_found


def _nginx_valid(filename: str) -> bool:
    """Check whether file with `filename` contains wide nginx configuration.

    Search for wide range of files in locations:

      location / {
        try_files $uri $uri/ /index.php?$query_string;
      }

    Args:
      filename: nginx config filename

    Returns:
        (bool): flag whether nginx config is valid

    """
    config = crossplane.parse(filename)
    if config["status"] != "ok":
        for error in config["errors"]:
            file, traceback = error["file"], error["error"]
            print(f"[PARSE ERROR] {file}: {traceback}")
            return False

    # crossplane config will contain all files which are attached to main
    # `nginx.conf` (i.e. `include` directives)
    try_files_entries, locations_entries = [], []
    for file in config["config"]:
        for directive in file["parsed"]:
            directive["file"] = file["file"]
            try_files_entries.extend(
                _search_directive(config=directive, name="try_files"),
            )
            locations_entries.extend(
                _search_directive(config=directive, name="location"),
            )

    # check whether `try_files` directive contains wide args
    nginx_valid = True
    wide_directives = []
    for directive in try_files_entries:
        args_lower = [arg.lower() for arg in directive["args"]]
        if any(item in args_lower for item in ["$uri", "$uri/"]):
            wide_directives.append(directive)
            nginx_valid = False

    # check whether all disabled `locations` directives exist, if all such
    # `locations` would be found, wide `try_files` directives may be ignored
    if not nginx_valid:
        if _disabled_locations_exist(locations_entries):
            nginx_valid = True

    # notify user about found wide directives if `nginx` config is not valid
    if not nginx_valid:
        for directive in wide_directives:
            print(
                f"[ERROR] wide `try_files` directive found: file "
                f'`{directive["file"]}`, {directive["line"]} line',
            )

    return nginx_valid


def validate_nginx_wide_range(
    filenames: Sequence[str] = [],
    nginx_config_path: str = "nginx.conf",
) -> int:
    """Validate nginx configuration files for `wide` range.

    Args:
      filenames: filenames that should be scanned
      nginx_config_path: path to main `nginx.conf` file to parse.

    Search for wide range of files in locations of `nginx.conf` and included to
    it files:

      location / {
        try_files $uri $uri/ /index.php?$query_string;
      }

    Returns:
        (int): flag whether nginx config is valid or not, 0 - success, 1 - error

    """
    retval = 0
    for filename in filenames:
        if nginx_config_path not in filename.lower():
            continue
        success = _nginx_valid(filename)
        if not success:
            retval = 1
    return retval


def main(argv: Sequence[str] | None = None) -> int:
    """Process hook args before calling main `validate_nginx_wide_range` action."""
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")
    parser.add_argument("-c", "--nginx_config_path", nargs=1, default=["nginx.conf"])
    args = parser.parse_args(argv)

    return validate_nginx_wide_range(args.filenames, args.nginx_config_path[0])


if __name__ == "__main__":
    raise SystemExit(main())
