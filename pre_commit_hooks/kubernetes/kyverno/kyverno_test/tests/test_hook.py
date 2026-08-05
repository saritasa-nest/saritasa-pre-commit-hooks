import os
import shutil
from pathlib import Path

import pytest

from pre_commit_hooks import util
from pre_commit_hooks.kubernetes.kyverno.kyverno_test.context import Context
from pre_commit_hooks.kubernetes.kyverno.kyverno_test.exceptions import ValidationError
from pre_commit_hooks.kubernetes.kyverno.kyverno_test.main import Hook
from pre_commit_hooks.kubernetes.kyverno.kyverno_test.validator import Validator


@pytest.fixture
def hook():
    """Constructs a hook."""
    context = Context(
        policies_directory=Path("config/policies"),
        tests_directory=Path("config/tests"),
        test_filename="kyverno-test.yaml",
        extra_arguments=[],
        ignored_paths={"kustomization.yaml"},
        fail_on_warnings=True
    )
    return Hook(context)


@pytest.fixture
def validator(hook):
    """Constructs a validator."""
    return Validator(hook.context)


@pytest.fixture
def temp_git_dir(tmpdir):
    """Prepare a temporary Git repository."""
    git_dir = tmpdir.join("tmpgit")
    util.git_init(git_dir)
    return git_dir


def _create_files(git_dir, *, commited=[], staged=[]):
    """Creates commited and staged files in a Git directory."""
    def create(root, path):
        segments = path.split("/")
        root.join(*segments).write("", ensure=True)

    with git_dir.as_cwd():
        for file in commited:
            create(git_dir, file)
        util.git_add()
        util.git_commit("Commited files")
        for file in staged:
            create(git_dir, file)
        util.git_add()


def _delete_files(git_dir, files):
    """Deletes files in a Git directory."""
    with git_dir.as_cwd():
        for file in files:
            segments = file.split("/")
            git_dir.join(*segments).remove(rec=0)
        util.git_add()


def _prepare_assets(git_dir, assets_dir_name):
    """Prepares assets for the test."""
    assets_root = os.path.join(os.path.dirname(__file__), "assets")
    source = os.path.join(assets_root, assets_dir_name)
    shutil.copytree(source, git_dir, dirs_exist_ok=True)
    with git_dir.as_cwd():
        util.git_add()


def test_get_policy_name(hook):
    """Tests policy name retrieval from a file path."""
    assert hook._get_policy_name("") is None
    assert hook._get_policy_name(".gitignore") is None
    assert hook._get_policy_name("config/dir") is None
    assert hook._get_policy_name("config/tests") is None
    assert hook._get_policy_name("config/dir/policies") is None
    assert hook._get_policy_name("config/policies") is None
    assert hook._get_policy_name("config/tests/prevent-injection.yaml") is None
    assert hook._get_policy_name("policies/prevent-injection.yaml") is None
    assert hook._get_policy_name("config/policies/policies/prevent-injection.yaml") is None
    assert hook._get_policy_name("root/config/policies/prevent-injection.yaml") is None
    assert hook._get_policy_name("config/policies/prevent-injection.yaml") == "prevent-injection"
    assert hook._get_policy_name("config/policies/kustomization.yaml") is None


def test_get_test_directory_name(hook):
    """Tests test directory name retrieval from a file path."""
    assert hook._get_test_directory_name("") is None
    assert hook._get_test_directory_name(".pre-commit-config.yaml") is None
    assert hook._get_test_directory_name("dir") is None
    assert hook._get_test_directory_name("tests") is None
    assert hook._get_test_directory_name("dir/tests") is None
    assert hook._get_test_directory_name("config/tests") is None
    assert hook._get_test_directory_name("config/tests/prevent-injection") is None
    assert hook._get_test_directory_name("config/tests/prevent-injection.yaml") is None
    assert hook._get_test_directory_name("root/config/tests/prevent-injection.yaml") is None
    assert hook._get_test_directory_name("config/tests/prevent-injection/resource.yaml") == "prevent-injection"
    assert hook._get_test_directory_name("config/tests/prevent-injection/assets/some.yaml") == "prevent-injection"
    assert hook._get_test_directory_name("config/tests/prevent-injection/assets/misc/more.yaml") == "prevent-injection"


def test_find_targets_in_unrelated_changes(temp_git_dir, hook):
    """Tests target discovery in unrelated changes."""
    with temp_git_dir.as_cwd():
        _create_files(temp_git_dir, staged=["README.md"])
        assert hook._find_targets() == set()


def test_find_targets_on_new_policy(temp_git_dir, hook):
    """Tests target discovery when a new policy is added."""
    with temp_git_dir.as_cwd():
        _create_files(temp_git_dir, staged=["config/policies/prevent-injection.yaml"])
        assert hook._find_targets() == {"prevent-injection"}


def test_find_targets_on_changed_policy(temp_git_dir, hook):
    """Tests target discovery when a single policy is changed."""
    with temp_git_dir.as_cwd():
        policies = [
            "config/policies/enforce-limits.yaml",
            "config/policies/prevent-injection.yaml"
        ]
        changed_policy = ["config/policies/add-security-context.yaml"]
        _create_files(temp_git_dir, commited=policies, staged=changed_policy)
        assert hook._find_targets() == {"add-security-context"}


def test_find_targets_on_changed_policies(temp_git_dir, hook):
    """Tests target discovery when multiple policies are changed."""
    with temp_git_dir.as_cwd():
        policy = ["config/policies/prevent-injection.yaml"]
        changed_policies = [
            "config/policies/add-security-context.yaml",
            "config/policies/enforce-limits.yaml"
        ]
        _create_files(temp_git_dir, commited=policy, staged=changed_policies)
        assert hook._find_targets() == {
            "add-security-context",
            "enforce-limits"
        }


def test_find_targets_on_new_test(temp_git_dir, hook):
    """Tests target discovery when a new test is added."""
    with temp_git_dir.as_cwd():
        _create_files(temp_git_dir, staged=["config/tests/prevent-injection/kyverno-test.yaml"])
        assert hook._find_targets() == {"prevent-injection"}


def test_find_targets_on_changed_test(temp_git_dir, hook):
    """Tests target discovery when a single test is changed."""
    with temp_git_dir.as_cwd():
        test_files = [
            "config/tests/enforce-limits/kyverno-test.yaml",
            "config/tests/enforce-limits/resource.yaml",
            "config/tests/prevent-injection/kyverno-test.yaml"
        ]
        changed_test_file = ["config/tests/prevent-injection/resource.yaml"]
        _create_files(temp_git_dir, commited=test_files, staged=changed_test_file)
        assert hook._find_targets() == {"prevent-injection"}


def test_find_targets_on_changed_tests(temp_git_dir, hook):
    """Tests target discovery when multiple tests are changed."""
    with temp_git_dir.as_cwd():
        test_files = [
            "config/tests/add-security-context/resource.yaml",
            "config/tests/prevent-injection/kyverno-test.yaml",
            "config/tests/prevent-injection/resource.yaml"
        ]
        changed_test_files = [
            "config/tests/add-security-context/kyverno-test.yaml",
            "config/tests/enforce-limits/kyverno-test.yaml",
            "config/tests/enforce-limits/resource.yaml"
        ]
        _create_files(temp_git_dir, commited=test_files, staged=changed_test_files)
        assert hook._find_targets() == {
            "add-security-context",
            "enforce-limits"
        }


def test_find_targets_on_combined_changes(temp_git_dir, hook):
    """Tests target discovery when policies and tests are changed."""
    with temp_git_dir.as_cwd():
        files = [
            "config/policies/add-security-context.yaml",
            "config/policies/prevent-injection.yaml",
            "config/tests/add-security-context/kyverno-test.yaml",
            "config/tests/enforce-limits/kyverno-test.yaml",
            "config/tests/enforce-limits/resource.yaml",
            "config/tests/prevent-injection/kyverno-test.yaml",
            "config/tests/prevent-injection/resource.yaml",
            ".gitignore",
            "README.md"
        ]
        changed_files = [
            "config/policies/enforce-limits.yaml",
            "config/policies/kustomization.yaml",
            "config/tests/add-security-context/resource.yaml"
        ]
        _create_files(temp_git_dir, commited=files, staged=changed_files)
        assert hook._find_targets() == {
            "add-security-context",
            "enforce-limits"
        }


def test_find_targets_on_deletion_in_tests(temp_git_dir, hook):
    """Tests target discovery when a file is deleted from a test directory."""
    with temp_git_dir.as_cwd():
        files = [
            "config/tests/enforce-limits/kyverno-test.yaml",
            "config/tests/enforce-limits/resource.yaml",
            "config/tests/prevent-injection/kyverno-test.yaml",
            "config/tests/prevent-injection/resource.yaml"
        ]
        _create_files(temp_git_dir, staged=files)
        util.git_commit("Added tests")
        _delete_files(temp_git_dir, ["config/tests/enforce-limits/resource.yaml"])
        assert hook._find_targets() == {"enforce-limits"}


def test_find_targets_on_combined_deletion(temp_git_dir, hook):
    """Tests target discovery when files are deleted from policies and tests."""
    with temp_git_dir.as_cwd():
        files = [
            "config/policies/enforce-limits.yaml",
            "config/policies/prevent-injection.yaml",
            "config/tests/enforce-limits/kyverno-test.yaml",
            "config/tests/enforce-limits/resource.yaml",
            "config/tests/prevent-injection/kyverno-test.yaml",
            "config/tests/prevent-injection/resource.yaml"
        ]
        _create_files(temp_git_dir, staged=files)
        util.git_commit("Added policies and tests")
        _delete_files(temp_git_dir, [
            "config/policies/enforce-limits.yaml",
            "config/tests/enforce-limits/resource.yaml"
        ])
        assert hook._find_targets() == set()


def test_validator_policy_file(temp_git_dir, validator):
    """Tests validator on a non-file policy."""
    _prepare_assets(temp_git_dir, "policy-not-a-file")
    with temp_git_dir.as_cwd(), pytest.raises(ValidationError) as e:
        validator.validate()
    assert "config/policies/enforce-limits is not a file" in str(e)


def test_validator_policy_name(temp_git_dir, validator):
    """Tests validator on a policy that has a name different from its file."""
    _prepare_assets(temp_git_dir, "policy-name-mismatch")
    with temp_git_dir.as_cwd(), pytest.raises(ValidationError) as e:
        validator.validate()
    assert "config/policies/enforce-limits.yaml has a nonmatching name: " \
        "enforce-limits ≠ enforce-lower-limits" in str(e)


def test_validator_test_directory(temp_git_dir, validator):
    """Tests validator on a non-directory test."""
    _prepare_assets(temp_git_dir, "test-not-a-directory")
    with temp_git_dir.as_cwd(), pytest.raises(ValidationError) as e:
        validator.validate()
    assert "config/tests/add-emptydir-sizelimit.yaml is not a directory" in str(e)


def test_validator_test_directory_name(temp_git_dir, validator):
    """Tests validator on a test not named after a policy."""
    _prepare_assets(temp_git_dir, "test-not-named-after-policy")
    with temp_git_dir.as_cwd(), pytest.raises(ValidationError) as e:
        validator.validate()
    assert "config/tests/emptydir-sizelimit is not named after a policy" in str(e)


def test_validator_no_manifest(temp_git_dir, validator):
    """Tests validator on a test without a manifest."""
    _prepare_assets(temp_git_dir, "no-test-manifest")
    with temp_git_dir.as_cwd(), pytest.raises(ValidationError) as e:
        validator.validate()
    assert "config/tests/add-emptydir-sizelimit/kyverno-test.yaml does not exist" in str(e)


def test_validator_multiple_manifests(temp_git_dir, validator):
    """Tests validator on a test with multiple manifests."""
    _prepare_assets(temp_git_dir, "multiple-test-manifests")
    with temp_git_dir.as_cwd(), pytest.raises(ValidationError) as e:
        validator.validate()
    assert "config/tests/add-emptydir-sizelimit contains multiple kyverno-test.yaml files" in str(e)


def test_validator_manifest_malformed_reference(temp_git_dir, validator):
    """Tests validator on a manifest with a malformed policy reference."""
    _prepare_assets(temp_git_dir, "malformed-policy-reference")
    with temp_git_dir.as_cwd(), pytest.raises(ValidationError) as e:
        validator.validate()
    assert "config/tests/add-emptydir-sizelimit/kyverno-test.yaml has a malformed policy reference" in str(e)


def test_validator_manifest_wrong_reference(temp_git_dir, validator):
    """Tests validator on a manifest that references a policy with a different name."""
    _prepare_assets(temp_git_dir, "wrong-policy-reference")
    with temp_git_dir.as_cwd(), pytest.raises(ValidationError) as e:
        validator.validate()
    assert "config/tests/add-emptydir-sizelimit/kyverno-test.yaml references a wrong policy: " \
        "expected add-emptydir-sizelimit.yaml, got emptydir-sizelimit.yaml" in str(e)


def test_validator_mutating_policy(temp_git_dir, validator):
    """Tests validator on a MutatingPolicy."""
    _prepare_assets(temp_git_dir, "mutating-policy")
    with temp_git_dir.as_cwd():
        validator.validate()


def test_run_on_correct_policy(temp_git_dir, hook):
    """Tests run on a correct policy."""
    _prepare_assets(temp_git_dir, "correct-policy")
    with temp_git_dir.as_cwd():
        exit_code = hook.run(strict=True)
    assert exit_code == 0


def test_run_on_incorrect_policy(temp_git_dir, hook):
    """Tests run on an incorrect policy."""
    _prepare_assets(temp_git_dir, "incorrect-policy")
    with temp_git_dir.as_cwd():
        exit_code = hook.run(strict=True)
    assert exit_code == 1
