from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Self


@dataclass
class Context:
    """Represents the context of the environment in which the hook is run.

    Attributes:
        policies_directory: Path to the policies directory.
        tests_directory: Path to the tests directory.
        test_filename: Name of the test manifest file.
        extra_arguments: List of additional arguments for `kyverno test`.
        ignored_paths: Set of ignored paths in the policies directory.
        fail_on_warnings: Feature toggle to enable failing on warnings.
    """
    policies_directory: Path
    tests_directory: Path
    test_filename: str
    extra_arguments: list[str]
    ignored_paths: set[str]
    fail_on_warnings: bool

    @classmethod
    def from_namespace(cls, namespace: Namespace) -> Self:
        """Constructs a context from a namespace.

        Args:
            namespace: A namespace object with context data.

        Returns:
            A constructed context.

        Raises:
            ValueError: If a namespace is missing a required key.
        """
        try:
            policies = Path(namespace.policies)
            tests = Path(namespace.tests)
            filename = namespace.test_filename
            extra_args = namespace.extra_args.split()
            ignored_paths = set(namespace.ignore_path)
            fail_on_warnings = not namespace.disable_fail_on_warnings
        except AttributeError as e:
            raise ValueError(f"Namespace is missing a key: {e.name}") from e
        return cls(
            policies,
            tests,
            filename,
            extra_args,
            ignored_paths,
            fail_on_warnings
        )
