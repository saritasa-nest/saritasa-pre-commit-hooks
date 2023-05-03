from __future__ import annotations

import pytest

from pre_commit_hooks.util import *


@pytest.fixture
def temp_git_dir(tmpdir):
    """Create temporary `gits` directory for tests."""
    git_dir = tmpdir.join("gits")
    git_init(git_dir)
    yield git_dir


@pytest.fixture
def temp_git_dir_with_files(temp_git_dir):
    """Create temporary `gits` directory for tests with random files."""
    with temp_git_dir.as_cwd():
        temp_file_1 = temp_git_dir.join("tmp1.txt")
        temp_file_1.write("Example text")
        temp_file_2 = temp_git_dir.mkdir("tmpdir").join("tmp2.txt")
        temp_file_2.write("Example text")
        git_add()
        yield temp_git_dir


@pytest.fixture
def locations():
    """Nginx config example with disabled `locations` directives."""
    yield [
        {
            "directive": "location",
            "args": ["~", "\.(json|sh|xml|md|conf|toml|yml|yaml|log|pid)$"],
            "block": [{"args": ["all"], "directive": "deny"}],
        },
        {
            "directive": "location",
            "args": ["~", "/cron.*"],
            "block": [{"args": ["all"], "directive": "deny"}],
        },
        {
            "directive": "location",
            "args": ["~", "/\\."],
            "block": [{"args": ["all"], "directive": "deny"}],
        },
        {
            "directive": "location",
            "args": ["~", "autodiscover.xml"],
            "block": [{"args": ["403"], "directive": "return"}],
        },
        {
            "directive": "location",
            "args": ["~", "apple-touch-icon"],
            "block": [{"args": ["403"], "directive": "return"}],
        },
        {
            "directive": "location",
            "args": [
                "~",
                "^/(app/|vendor|src|tests|vagrant|docs|phpunit|svn|git|docker|migrations|Makefile)",
            ],
            "block": [{"args": ["403"], "directive": "return"}],
        },
    ]


@pytest.fixture
def messed_locations(locations):
    """Nginx config example with disabled `locations` directives in messed order."""
    locations[0]["args"][1] = "\.(conf|json|toml|md|log|sh|yml|xml|pid|yaml)$"
    locations[-1]["args"][
        1
    ] = "^/(src|tests|app/|vendor|phpunit|svn|vagrant|docs|migrations|Makefile|git|docker)"
    yield locations
