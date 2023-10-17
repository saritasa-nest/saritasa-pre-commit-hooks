import argparse
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import crossplane

DEFAULT_DENY_LOCATIONS = [
    "/cron.*",
    "/\.",
    "autodiscover.xml",
    "apple-touch-icon",
    "\.(json|sh|xml|md|conf|toml|yml|yaml|log|pid)$",
    "^/(app/|vendor|src|tests|vagrant|docs|phpunit|svn|git|docker|migrations|Makefile)",
]


DEFAULT_NGINX_CONFIG_PATH = "nginx.conf"


@dataclass
class SearchItem:
    """Dataclass to represent searched by regex item."""

    regex: str
    expected: str
    exists: bool = False


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


def _disabled_locations_exist(
    locations: List[Dict] | None = None,
    custom_deny_locations: List[str] | None = None,
    extra_deny_locations: List[str] | None = None,
) -> bool:
    """Check that all corresponding `disabled` locations were added.

    Search for below directives in nginx config, if at least one of them
    is not defined - error will be raised:

        location ~ \.(json|sh|xml|md|conf|toml|yml|yaml|log|pid)$  {deny all;}
        location ~ /cron.*                                              {deny all;}
        location ~ /\.                                                  {deny all;}
        location ~ autodiscover.xml {return 403;}
        location ~ apple-touch-icon {return 403;}
        location ~ ^/(app/|vendor|src|tests|vagrant|docs|phpunit|svn|git|docker|migrations|Makefile) {return 403;}

    Args:
      locations: list with all `locations` directives configs found in nginx config
      custom_deny_locations: custom deny locations, overrides existing ones
      extra_deny_locations: extra deny locations, adds to existing ones

    Returns:
      (bool): flag whether all required disabled `locations` directives are added

    """
    locations = locations or []
    custom_deny_locations = custom_deny_locations or []
    extra_deny_locations = extra_deny_locations or []

    # if `custom_deny_locations` were passed use it + `extra_deny_locations`,
    # otherwise use `default_deny_locations` + `extra_deny_locations`
    matches = (custom_deny_locations or DEFAULT_DENY_LOCATIONS) + extra_deny_locations
    regex_matches = [SearchItem(regex=rf"^{re.escape(item)}$", expected=item) for item in matches]

    for location in locations:
        location_prefix = location["args"][0]
        if location_prefix != "~":
            continue

        for item in regex_matches:
            location_name = location["args"][1]
            if not re.match(item.regex, location_name):
                continue

            deny = _search_directive(config=location, name="deny", value=["all"])
            return_403 = _search_directive(config=location, name="return", value=["403"])

            if deny or return_403:
                item.exists = True

    all_disabled_locations_found = True
    for item in regex_matches:
        if item.exists is not True:
            all_disabled_locations_found = False
            print(
                f"[ERROR] location not disabled: `location ~ {item.expected}`. "
                "Please disable it with `{{deny all;}}` or `{{return 403;}}` directives.",
            )

    return all_disabled_locations_found


def _has_parse_errors(
    config: dict,
    ignore_errors_keywords: List[str] | None = None,
) -> bool:
    """Check whether parsed config has errors.

    Sometimes projects use `include` directives without real files presence in
    the repo (these files are added as nginx defaults during installation) -
    https://github.com/nginx/nginx/tree/master/conf. Errors with such keywords
    are added to `ignored` list by default.

    Args:
      config: parsed nginx congfig
      ignore_errors_keywords: keywords that contained in errors to be ignored

    Returns:
        (bool): flag whether nginx config has parse errors

    """
    if config["status"] == "ok":
        return False

    ignore_errors_keywords = ignore_errors_keywords or []
    ignore_errors_keywords.extend([
        "fastcgi_params", "koi-utf", "koi-win", "mime.types",
        "scgi_params", "uwsgi_params", "win-utf",
    ])

    for error in config["errors"]:
        file, traceback = error["file"], error["error"]

        # do not process errors from `ignore_errors_keywords`
        if any(keyword in traceback for keyword in ignore_errors_keywords):
            continue

        print(f"[PARSE ERROR] {file}: {traceback}")
        return True
    return False


def _nginx_valid(
    filename: str,
    custom_deny_locations: List[str] | None = None,
    extra_deny_locations: List[str] | None = None,
    ignore_errors_keywords: List[str] | None = None,
) -> bool:
    """Check whether file with `filename` contains wide nginx configuration.

    Search for wide range of files in locations:

      location / {
        try_files $uri $uri/ /index.php?$query_string;
      }

    Args:
      filename: nginx config filename
      custom_deny_locations: custom deny locations, overrides existing ones
      extra_deny_locations: extra deny locations, adds to existing ones
      ignore_errors_keywords: keywords that contained in errors to be ignored

    Returns:
        (bool): flag whether nginx config is valid

    """
    config = crossplane.parse(filename)
    if _has_parse_errors(config, ignore_errors_keywords):
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
        if _disabled_locations_exist(
            locations_entries,
            custom_deny_locations,
            extra_deny_locations,
        ):
            return True

        # notify user about found wide directives if `nginx` config is not valid
        for directive in wide_directives:
            print(
                f"[ERROR] wide `try_files` directive found: file "
                f'`{directive["file"]}`, {directive["line"]} line',
            )

    return nginx_valid


def validate_nginx_wide_range(
    filenames: Sequence[str] | None = None,
    nginx_config_path: str = "",
    custom_deny_locations: List[str] | None = None,
    extra_deny_locations: List[str] | None = None,
    ignore_errors_keywords: List[str] | None = None,
) -> int:
    """Validate nginx configuration files for `wide` range.

    Args:
      filenames: filenames that should be scanned
      nginx_config_path: path to main `nginx.conf` file to parse
      custom_deny_locations: custom deny locations, overrides existing ones
      extra_deny_locations: extra deny locations, adds to existing ones
      ignore_errors_keywords: keywords that contained in errors to be ignored

    Search for wide range of files in locations of `nginx.conf` and included to
    it files:

      location / {
        try_files $uri $uri/ /index.php?$query_string;
      }

    Returns:
        (int): flag whether nginx config is valid or not, 0 - success, 1 - error

    """
    filenames = filenames or []
    retval = 0

    # use default `nginx.conf` path only if it exists (to not raise error for
    # not frontend repos if they have no default `nginx.conf`), but if custom
    # `nginx_config_path` was passed - force user to have it
    if not nginx_config_path:
        if os.path.exists(DEFAULT_NGINX_CONFIG_PATH):
            nginx_config_path = DEFAULT_NGINX_CONFIG_PATH
        # do nothing when no `nginx_config_path` value was passed and no
        # default nginx.conf exists
        else:
            return retval

    # try to find nginx.conf files from commited filenames or use `nginx_config_path`
    # if it exists even if it is not committed when `*.conf` files commited
    committed_nginx_configs = list(filter(lambda filename: nginx_config_path in filename.lower(), filenames))
    committed_conf_files = list(filter(lambda filename: re.match(".*\.conf$", filename), filenames))
    if not committed_nginx_configs and committed_conf_files:
        committed_nginx_configs = [nginx_config_path]

    for config in committed_nginx_configs:
        success = _nginx_valid(
            config,
            custom_deny_locations,
            extra_deny_locations,
            ignore_errors_keywords,
        )
        if not success:
            retval = 1
    return retval


def main(argv: Sequence[str] | None = None) -> int:
    """Process hook args before calling main `validate_nginx_wide_range` action."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filenames",
        nargs="*",
        help="Committed files",
    )
    parser.add_argument(
        "--nginx_config_path",
        nargs=1,
        default=[""],
        help="Nginx config path",
    )
    parser.add_argument(
        "--custom_deny_locations",
        nargs="*",
        default=[],
        help="Custom deny locations, overrides existing ones (i.e. '/cron.*')",
        action="append",
    )
    parser.add_argument(
        "--extra_deny_locations",
        nargs="*",
        default=[],
        help="Extra deny locations, adds to existing ones (i.e. '/cron.*')",
        action="append",
    )
    parser.add_argument(
        "--ignore_errors_keywords",
        nargs="*",
        default=[],
        help=(
            "Extra keywords which are contained in errors to be ignored, adds "
            "to existing ones, default: fastcgi_params, koi-utf, koi-win, "
            "mime.types, scgi_params, uwsgi_params, win-utf"
        ),
        action="append",
    )
    args = parser.parse_args(argv)

    return validate_nginx_wide_range(
        args.filenames,
        args.nginx_config_path[0],
        [item for sublist in args.custom_deny_locations for item in sublist],
        [item for sublist in args.extra_deny_locations for item in sublist],
        [item for sublist in args.ignore_errors_keywords for item in sublist],
    )


if __name__ == "__main__":
    raise SystemExit(main())
