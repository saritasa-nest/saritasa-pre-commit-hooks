from contextlib import chdir
from functools import reduce
from pathlib import Path
from typing import Any

import yaml
from yaml import YAMLError

from .context import Context
from .exceptions import ValidationError


class Validator:
    """Test environment validator.

    The validator ensures that the environment of hook execution is in line
    with its assumptions about the file hierarchy and content.

    Attributes:
        context: The context of the environment.
    """
    context: Context

    def __init__(self, context: Context) -> None:
        """Initializes Validator.

        Args:
            context: The context of the environment.
        """
        self.context = context

    def _validate_yaml_manifest(self, path: Path, rules: dict) -> None:
        """Validates a YAML manifest at the given path using the rules.

        The dictionary of rules maps manifest keys to the corresponding validation
        lambdas. Given a value for the key as an argument, each lambda must return
        a boolean indicating whether the value is valid or not and, if the value
        is invalid, a non-empty message stating the reason.

        The keys support nesting using `~>` operator. For example, to get a value for
        the key `child.example.org` of mapping `parent`, the following string can be
        used: `parent~>child.example.org`.

        Args:
            path: Path to the YAML manifest.
            rules: Dictionary of validation rules.

        Raises:
            ValidationError: If the YAML manifest is not valid.
        """
        with open(path, "r") as file:
            try:
                manifest = yaml.safe_load(file)
            except YAMLError as e:
                raise ValidationError(f"{path} is not a valid YAML manifest") from e
        if not manifest:
            raise ValidationError(f"{path} is an empty file")

        dict_get = lambda d, k: d.get(k) if isinstance(d, dict) else None
        for key, handler in rules.items():
            value = reduce(dict_get, key.split("~>"), manifest)
            if value is None:
                raise ValidationError(f"{path} does not have a value for {key}")
            valid, message = handler(value)
            if not valid:
                raise ValidationError(message)

    def _validate_policy(self, path: Path) -> None:
        """Validates a policy manifest at the given path.

        Args:
            path: Path to the policy manifest.

        Raises:
            ValidationError: If the policy manifest is not valid.
        """
        def api_version_handler(api_version: Any) -> tuple[bool, str]:
            message = f"{path} has invalid apiVersion: {api_version}"
            if not isinstance(api_version, str):
                return (False, message)
            # `Policy` and `ClusterPolicy` live in the `kyverno.io` group, while
            # `MutatingPolicy` lives in `policies.kyverno.io`. An apiVersion is
            # exactly `group/version`, so both segments are required and nothing
            # may follow them.
            group, _, version = api_version.partition("/")
            groups = {"kyverno.io", "policies.kyverno.io"}
            return (group in groups and bool(version) and "/" not in version, message)

        def spec_handler(spec: Any) -> tuple[bool, str]:
            if not isinstance(spec, dict):
                return (False, f"{path} does not define a spec mapping")
            # `Policy` and `ClusterPolicy` declare `rules`, while `MutatingPolicy`
            # declares `mutations` instead.
            for key in ("rules", "mutations"):
                value = spec.get(key)
                if isinstance(value, list) and len(value) > 0:
                    return (True, "")
            return (False, f"{path} does not define a non-empty list of rules or mutations")

        self._validate_yaml_manifest(path, {
            "apiVersion": api_version_handler,
            "kind": lambda kind: (
                isinstance(kind, str) and kind in {
                    "Policy", "ClusterPolicy", "MutatingPolicy"
                },
                f"{path} is not a Policy, a ClusterPolicy or a MutatingPolicy, "
                f"it is a {kind}"
            ),
            "metadata~>name": lambda name: (
                isinstance(name, str) and name == path.stem,
                f"{path} has a nonmatching name: {path.stem} ≠ {name}"
            ),
            "spec": spec_handler
        })

    def _validate_policies(self) -> set[str]:
        """Validates policies directory.

        Returns:
            A set of valid policy names.

        Raises:
            ValidationError: If policies directory is not valid.
        """
        policies = self.context.policies_directory
        if not policies.is_dir():
            raise ValidationError(f"{policies} is not a directory")

        policies = [
            policy for policy in policies.iterdir()
            if policy.name not in self.context.ignored_paths
        ]

        for policy in policies:
            if not policy.is_file():
                raise ValidationError(f"{policy} is not a file")
            if policy.suffixes != [".yaml"]:
                raise ValidationError(f"{policy} is not a .yaml file")

        valid_policies = set()
        for policy in policies:
            self._validate_policy(policy)
            valid_policies.add(policy.stem)
        return valid_policies

    def _validate_test(self, path: Path) -> None:
        """Validates a test directory at the given path.

        Args:
            path: Path to the test directory.

        Raises:
            ValidationError: If the test directory is not valid.
        """
        filename = self.context.test_filename
        manifest_path = path / filename
        if not manifest_path.exists():
            raise ValidationError(f"{manifest_path} does not exist")
        manifest_count = 0
        for root, _, files in path.walk():
            manifest_count += 1 if filename in files else 0
            if manifest_count > 1:
                raise ValidationError(f"{path} contains multiple {filename} files")

        def policies_handler(policies: Any) -> tuple[bool, str]:
            if not isinstance(policies, list):
                return (False, f"{manifest_path} does not define a list of policies")
            if len(policies) != 1:
                return (False, f"{manifest_path} does not reference a single policy")
            if not isinstance(policies[0], str):
                return (False, f"{manifest_path} has a non-string policy reference")

            policy = Path(policies[0])
            with chdir(path):
                policy = policy.resolve()
            try:
                policy = policy.relative_to(Path.cwd())
            except ValueError:
                return (False, f"{manifest_path} has a malformed policy reference")

            if policy.parent != self.context.policies_directory:
                return (False, f"{manifest_path} references a policy outside of policies directory")
            if policy.name != f"{path.name}.yaml":
                return (False, f"{manifest_path} references a wrong policy: expected {path.name}.yaml, got {policy.name}")
            return (True, "")

        self._validate_yaml_manifest(manifest_path, {
            "apiVersion": lambda api_version: (
                isinstance(api_version, str) and api_version.startswith("cli.kyverno.io/"),
                f"{manifest_path} has invalid apiVersion: {api_version}"
            ),
            "kind": lambda kind: (
                isinstance(kind, str) and kind == "Test",
                f"{manifest_path} is not a Test, it is a {kind}"
            ),
            "policies": policies_handler,
            "results": lambda results: (
                isinstance(results, list) and len(results) > 0,
                f"{manifest_path} does not define a non-empty list of results"
            )
        })

    def _validate_tests(self, policy_names: set[str]) -> None:
        """Validates tests directory given a set of valid policy names.

        Args:
            policy_names: A set of valid policy names.

        Raises:
            ValidationError: If tests directory is not valid.
        """
        tests = self.context.tests_directory
        if not tests.is_dir():
            raise ValidationError(f"{tests} is not a directory")

        for test in tests.iterdir():
            if not test.is_dir():
                raise ValidationError(f"{test} is not a directory")
            if test.name not in policy_names:
                raise ValidationError(f"{test} is not named after a policy")

        for test in tests.iterdir():
            self._validate_test(test)

    def validate(self) -> None:
        """Validates the environment of hook execution.

        Raises:
            ValidationError: If the environment is not valid.
        """
        valid_policies = self._validate_policies()
        self._validate_tests(valid_policies)
