#!/usr/bin/env python3

import sys

from pre_commit_hooks.util import git_hash_object_stdin, is_ancestor

# Error message printed when a force push is detected
FORCE_PUSH_ERROR = "[ERROR] Refusing force (non-fast-forward) push on {remote_ref}."


def validate_push() -> int:
    """Read pre-push hook's stdin lines of the format: `<local_ref> <local_sha> <remote_ref> <remote_sha>`.

    Args:
        none

    Returns:
      int: 0 if all updates are fast-forward (push allowed), 1 if any non-fast-forward is detected.

    """
    # Make a string of 0s of the hash-object length, for later comparison
    zero_sha = "0" * len(git_hash_object_stdin())

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        local_ref, local_sha, remote_ref, remote_sha = line.split()

        # If local_sha == zero_sha, this is a branch deletion; skip
        if local_sha == zero_sha:
            continue

        # If remote_sha == zero_sha, this is a new branch; skip
        if remote_sha == zero_sha:
            continue

        # Check whether remote_sha is an ancestor of local_sha
        if not is_ancestor(remote_sha, local_sha):
            # If no, this is a force (non-fast-forward) push
            # Prevent git push and print out an error
            print(FORCE_PUSH_ERROR.format(remote_ref=remote_ref))
            return 1

    return 0


if __name__ == "__main__":
    # Exit the script with the returned status code
    sys.exit(validate_push())
