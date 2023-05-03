import os
import shutil
from copy import deepcopy
from typing import List

from pre_commit_hooks.check_nginx_wide_range import (
    _disabled_locations_exist,
    validate_nginx_wide_range,
)
from pre_commit_hooks.util import *


def _prepare_test(dirname: str, git_dir: str) -> List[str]:
    """Prepare to test ecxecution.

    1. Copy corresponding test folder contents to `git_dir`.
    2. Perform `git add .` command in `git_dir`.
    3. Get list of git staged filenames.

    Returns:
      (list): list of filenames staged in git

    """
    with git_dir.as_cwd():
        copy_path = os.path.join(get_testing_path(), f"{dirname}/")
        shutil.copytree(copy_path, git_dir, dirs_exist_ok=True)
        git_add()
        filenames = git_diff_staged_files()
        return filenames


def test_nothing_added(temp_git_dir):
    """Check hook runs without errors if no files are in commit."""
    with temp_git_dir.as_cwd():
        assert validate_nginx_wide_range() == 0


def test_no_nginx_files(temp_git_dir_with_files):
    """Check hook runs without errors if no nginx files are in commit."""
    with temp_git_dir_with_files.as_cwd():
        filenames = git_diff_staged_files()
        assert validate_nginx_wide_range(filenames) == 0


def test_no_try_files(temp_git_dir_with_files):
    """Check hook runs without errors if no `try_files` directive exists."""
    with temp_git_dir_with_files.as_cwd():
        filenames = _prepare_test("no-try-files", temp_git_dir_with_files)
        assert validate_nginx_wide_range(filenames) == 0


def test_not_wide_try_files(temp_git_dir_with_files):
    """Check hook runs without errors if not wide `try_files` directive exists."""
    with temp_git_dir_with_files.as_cwd():
        filenames = _prepare_test("not-wide-try-files", temp_git_dir_with_files)
        assert validate_nginx_wide_range(filenames) == 0


def test_wide_try_files_no_disabled_locations(temp_git_dir_with_files, capsys):
    """Check hook fails when `try_files` directive exists without disabled locations."""
    with temp_git_dir_with_files.as_cwd():
        filenames = _prepare_test(
            "wide-try-files-no-disabled-locations",
            temp_git_dir_with_files,
        )
        assert validate_nginx_wide_range(filenames) == 1
        captured = capsys.readouterr()
        expected_error = (
            "[ERROR] wide `try_files` directive found: "
            "file `nginx.d/locations_allowed.conf`, 7 line"
        )
        assert expected_error in captured.out


def test_wide_try_files_with_locations_path(temp_git_dir_with_files, capsys):
    """Check hook fails when wide `try_files` directive exists for some path (i.e. `location /api`)."""
    with temp_git_dir_with_files.as_cwd():
        filenames = _prepare_test(
            "wide-try-files-with-location-path",
            temp_git_dir_with_files,
        )
        assert validate_nginx_wide_range(filenames) == 1
        captured = capsys.readouterr()
        expected_error = (
            "[ERROR] wide `try_files` directive found: "
            "file `.nginx/locations_allowed.conf`, 2 line"
        )
        assert expected_error in captured.out


def test_wide_try_files_with_disabled_locations_different_config_name(
    temp_git_dir_with_files,
):
    """Check hook runs ok when custom nginx config filename is passed."""
    with temp_git_dir_with_files.as_cwd():
        filenames = _prepare_test(
            "wide-try-files-with-disabled-locations-different-config-name",
            temp_git_dir_with_files,
        )
        assert validate_nginx_wide_range(filenames, "custom.conf") == 0


def test_wide_try_files_with_disabled_locations(temp_git_dir_with_files):
    """Check hook runs without errors if `try_files` directive exists, but correct disabled locations defined."""
    with temp_git_dir_with_files.as_cwd():
        filenames = _prepare_test(
            "wide-try-files-with-disabled-locations",
            temp_git_dir_with_files,
        )
        assert validate_nginx_wide_range(filenames) == 0


def test_disabled_locations_exist_messed_order(messed_locations):
    """Check `_disabled_locations_exist` method with messed directives order."""
    assert _disabled_locations_exist(messed_locations)


def test_disabled_locations_exist_not_all_directives_added(locations, capsys):
    """Check `_disabled_locations_exist` method when not all directives added."""
    for idx, item in enumerate(locations):
        locations_copy = deepcopy(locations)
        locations_copy.pop(idx)
        assert not _disabled_locations_exist(locations_copy)
        captured = capsys.readouterr()
        assert "[ERROR] location not disabled:" in captured.out
        assert item["args"][1] in captured.out


def test_disabled_locations_exist_not_all_directives_regex_values_added(
    locations,
    capsys,
):
    """Check `_disabled_locations_exist` method when not all directives regex `values` added."""
    locations_copy = deepcopy(locations)

    # check not all values added in `\.(json|sh|xml|md|conf|toml|yml|yaml|log|pid)$` location
    locations_copy[0]["args"][1] = "\.(json|sh|md|conf|yml|log|pid)$"
    assert not _disabled_locations_exist(locations_copy)
    captured = capsys.readouterr()
    assert "[ERROR] location not disabled:" in captured.out
    assert locations[0]["args"][1] in captured.out

    # check not all values added in
    # `^/(app/|vendor|src|tests|vagrant|docs|phpunit|svn|git|docker|migrations|Makefile)` location
    locations_copy[-1]["args"][1] = "^/(app/|docs|phpunit|svn|git|docker)"
    assert not _disabled_locations_exist(locations_copy)
    captured = capsys.readouterr()
    assert "[ERROR] location not disabled:" in captured.out
    assert locations[-1]["args"][1] in captured.out
