from __future__ import annotations

import os
import subprocess
from typing import Any


def cmd_output(*cmd: str, retcode: int | None = 0, **kwargs: Any) -> str:
    """Shortand to execute git commands in os or raise error if needed."""
    kwargs.setdefault("stdout", subprocess.PIPE)
    kwargs.setdefault("stderr", subprocess.PIPE)
    proc = subprocess.Popen(cmd, **kwargs)
    stdout, stderr = proc.communicate()
    stdout = stdout.decode()
    if retcode is not None and proc.returncode != retcode:
        raise RuntimeError(cmd, retcode, proc.returncode, stdout, stderr)
    return stdout


def get_testing_path():
    """Get `testing` folder path with different examples for tests."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "testing")


def git_init(git_dir: str = "."):
    """Shortand for `git init` command."""
    return cmd_output("git", "init", "--", git_dir)


def git_add(files: str = "."):
    """Shortand for `git add .` command."""
    return cmd_output("git", "add", files)


def git_reset(files: str = "."):
    """Shortand for `git reset` command."""
    return cmd_output("git", "reset", files)


def git_diff_staged_files():
    """Shortand for `git diff` command to get updates files."""
    return cmd_output("git", "diff", "--name-only", "--staged").strip().split("\n")
