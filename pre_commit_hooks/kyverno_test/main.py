import argparse
import subprocess
from collections.abc import Sequence
from pathlib import Path

from pre_commit_hooks.util import get_changed_files, get_deleted_files

from .context import Context
from .exceptions import KyvernoTestError, ValidationError
from .validator import Validator


class Hook:
    """Kyverno test pre-commit hook.

    Attributes:
        context: The context of the environment in which the hook is run.
    """
    context: Context

    def __init__(self, context: Context) -> None:
        """Initializes Hook.

        Args:
            context: The context of the environment in which the hook is run.
        """
        self.context = context

    def _get_policy_name(self, path: Path | str) -> str | None:
        """Retrieves a name of the policy corresponding to the path.

        If a file at the given path is a policy, its name will be used.

        Args:
            path: A repository file path.

        Returns:
            Name of the policy or None if no policy corresponds to the path.
        """
        path = Path(path)
        in_policies = path.parent == self.context.policies_directory
        not_ignored = path.name not in self.context.ignored_paths
        return path.stem if in_policies and not_ignored else None

    def _get_test_directory_name(self, path: Path | str) -> str | None:
        """Retrieves a name of the test directory corresponding to the path.

        If a file at the given path is located in some test directory, the name of
        this directory will be used. For example, the following path will produce
        `add-secret` as a return value: `tests/add-secret/results/bad-pod.yaml`
        (if `tests` is the tests directory of the context).

        Args:
            path: A repository file path.

        Returns:
            Name of the test directory or None if no directory corresponds to the path.
        """
        path = Path(path)
        try:
            index = path.parents.index(self.context.tests_directory)
        except ValueError:
            return None
        return path.parents[index - 1].name if index > 0 else None

    def _find_targets(self) -> set[str]:
        """Identifies targets for running tests by scanning staged files.

        The corresponding test is selected if:
        - any policy or test-related file is added or modified;
        - test-related file is deleted.

        If a policy is deleted, the tests run for it is canceled.

        Returns:
            A set of policy or test directory names to run tests for.
        """
        changes = get_changed_files()
        deletions = get_deleted_files()
        changed_policies = set(map(self._get_policy_name, changes))
        deleted_policies = set(map(self._get_policy_name, deletions))
        tests = set(map(self._get_test_directory_name, changes | deletions))
        return (changed_policies | tests) - deleted_policies - {None}

    def _kyverno_test(self, path: Path) -> None:
        """Runs `kyverno test` on a given test directory.

        Standard output and error streams are captured and analyzed for the presence
        of errors and, optionally, warnings. The errors do not always result in a
        non-zero exit code (e.g. an invalid test manifest with an unmarshaling error).

        Args:
            path: A path to the test directory.

        Raises:
            KyvernoTestError: If any error or warning is encountered, including test failure.
        """
        command = [
            "kyverno", "test", "--require-tests", "--detailed-results", "--fail-only",
            "--file-name", self.context.test_filename
        ]
        command.extend(self.context.extra_arguments)
        command.append(path)
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        got_warnings = self.context.fail_on_warnings and process.stdout.find(b"WARNING:") != -1
        got_errors = process.returncode != 0 or process.stdout.find(b"Test errors:") != -1
        if got_warnings or got_errors:
            raise KyvernoTestError("Failure", path, process.stdout, process.returncode)

    def run(self, strict: bool = True) -> int:
        """Runs tests for all the identified targets.

        In strict mode, the validation step is performed before running
        the tests. The mode is highly recommended, because it enforces
        the hook's assumptions about the environment.

        Args:
            strict: Feature toggle to enable strict mode.

        Returns:
            An exit code of the hook, zero on success.
        """
        if strict:
            try:
                Validator(self.context).validate()
            except ValidationError as e:
                print(f"Validation error: {e}")
                return 1
        for target in self._find_targets():
            try:
                self._kyverno_test(Path(self.context.tests_directory, target))
            except KyvernoTestError as e:
                print("", f"Failure @ {e.path}:", e.output.decode(), sep="\n", end="")
                return 1
        return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parses arguments and runs the hook.

    Args:
        argv: A sequence of command line arguments.

    Returns:
        An exit code of the hook, zero on success.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--policies", required=True, help="Path to policies directory")
    parser.add_argument("-t", "--tests", required=True, help="Path to tests directory")
    parser.add_argument("-f", "--test-filename", default="kyverno-test.yaml", help="Kyverno test filename")
    parser.add_argument("--extra-args", default="", help="Additional arguments for `kyverno test`")
    parser.add_argument("--ignore-path", action="append", default=[], help="Ignore a path in policies directory")
    parser.add_argument("--disable-strict-mode", action="store_true", help="Disable strict mode, skip validation")
    parser.add_argument("--disable-fail-on-warnings", action="store_true", help="Disable failing on warnings")
    args = parser.parse_args(argv)

    context = Context.from_namespace(args)
    strict = not args.disable_strict_mode

    return Hook(context).run(strict)


if __name__ == "__main__":
    raise SystemExit(main())
