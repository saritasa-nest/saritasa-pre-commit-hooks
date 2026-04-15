import pytest

from pre_commit_hooks.check_placeholders.main import (
    FOUND_PLACEHOLDER_MSG,
    MODE_BOTH,
    MODE_KUBERNETES,
    MODE_TERRAFORM,
    check_files,
)


@pytest.fixture
def test_file(tmp_path):
    """Fixture to create a temporary test file."""
    def create_file(name: str, text: str) -> str:
        path = tmp_path / name
        path.write_text(text, newline='\n')
        return str(path)
    return create_file


def test_no_unreplaced_placeholders_found(test_file, capsys):
    """Test that check_files returns 0 for files without unreplaced placeholders."""
    path = test_file("staging.tfvars", "namespace = 'staging'\n")

    exit_code = check_files([path], MODE_BOTH)
    assert exit_code == 0

    out, _ = capsys.readouterr()
    assert out == ""


def test_unreplaced_kubernetes_placeholder_found(test_file, capsys):
    """Test that check_files fails and prints the expected message for a kubernetes placeholder."""
    path = test_file("values.yaml", "aws_region: $AWS_REGION\n")

    exit_code = check_files([path], MODE_KUBERNETES)
    assert exit_code == 1

    out, _ = capsys.readouterr()
    assert FOUND_PLACEHOLDER_MSG.format(filename=path, line=1, column=13, placeholder="$AWS_REGION") in out


def test_unreplaced_terraform_placeholder_found(test_file, capsys):
    """Test that check_files fails and prints the expected message for a terraform placeholder."""
    path = test_file("prod.tfvars", 'route53_domain = "__DOMAIN__"\n')

    exit_code = check_files([path], MODE_TERRAFORM)
    assert exit_code == 1

    out, _ = capsys.readouterr()
    assert FOUND_PLACEHOLDER_MSG.format(filename=path, line=1, column=19, placeholder="__DOMAIN__") in out


def test_all_matches_across_files_found(test_file, capsys):
    """Test that check_files reports all unreplaced placeholders in all files."""
    path1 = test_file("values.yaml", "aws_region: $AWS_REGION\n")
    path2 = test_file("prod.tfvars", 'route53_domain = "__DOMAIN__"\n')

    exit_code = check_files([path1, path2], MODE_BOTH)
    assert exit_code == 1

    out, _ = capsys.readouterr()
    assert FOUND_PLACEHOLDER_MSG.format(filename=path1, line=1, column=13, placeholder="$AWS_REGION") in out
    assert FOUND_PLACEHOLDER_MSG.format(filename=path2, line=1, column=19, placeholder="__DOMAIN__") in out


def test_kubernetes_mode_ignores_terraform_placeholder(test_file, capsys):
    """Test that kubernetes mode ignores terraform-style placeholders."""
    path = test_file("prod.tfvars", 'route53_domain = "__DOMAIN__"\n')

    exit_code = check_files([path], MODE_KUBERNETES)
    assert exit_code == 0

    out, _ = capsys.readouterr()
    assert out == ""


def test_terraform_mode_ignores_kubernetes_placeholder(test_file, capsys):
    """Test that terraform mode ignores kubernetes-style placeholders."""
    path = test_file("values.yaml", "aws_region: $AWS_REGION\n")

    exit_code = check_files([path], MODE_TERRAFORM)
    assert exit_code == 0

    out, _ = capsys.readouterr()
    assert out == ""
