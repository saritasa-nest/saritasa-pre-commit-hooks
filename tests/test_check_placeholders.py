import pytest

from pre_commit_hooks.check_devops_templated_variables.main import FOUND_PLACEHOLDER_MSG, check_files


@pytest.fixture
def test_file(tmp_path):
    """Fixture to create a temporary test file."""
    def create_file(name: str, text: str) -> str:
        path = tmp_path / name
        path.write_text(text, newline='\n')
        return str(path)
    return create_file


@pytest.fixture
def placeholders_file(tmp_path):
    """Fixture to create a temporary placeholders file."""
    def create_file(text: str) -> str:
        path = tmp_path / ".placeholders"
        path.write_text(text, newline="\n")
        return str(path)
    return create_file


def test_no_unreplaced_placeholders_found(test_file, placeholders_file, capsys):
    """Test that check_files returns 0 for files without unreplaced placeholders."""
    placeholders = placeholders_file("DOMAIN\nPROJECT_NAME\n")
    path = test_file("staging.tfvars", "namespace = 'staging'\n")

    exit_code = check_files(
        [path],
        placeholders,
        [
            r"\${variable}",
            r"__{variable}__",
        ],
    )
    assert exit_code == 0

    out, _ = capsys.readouterr()
    assert out == ""


def test_unreplaced_kubernetes_placeholder_found(test_file, placeholders_file, capsys):
    """Test that check_files fails and prints the expected message for a kubernetes placeholder."""
    placeholders = placeholders_file("AWS_REGION\n")
    path = test_file("values.yaml", "aws_region: $AWS_REGION\n")

    exit_code = check_files(
        [path],
        placeholders,
        [r"\${variable}"],
    )
    assert exit_code == 1

    out, _ = capsys.readouterr()
    assert FOUND_PLACEHOLDER_MSG.format(
        filename=path,
        line=1,
        column=13,
        placeholder="$AWS_REGION",
    ) in out


def test_unreplaced_terraform_placeholder_found(test_file, placeholders_file, capsys):
    """Test that check_files fails and prints the expected message for a terraform placeholder."""
    placeholders = placeholders_file("DOMAIN\n")
    path = test_file("prod.tfvars", 'route53_domain = "__DOMAIN__"\n')

    exit_code = check_files(
        [path],
        placeholders,
        [r"__{variable}__"],
    )
    assert exit_code == 1

    out, _ = capsys.readouterr()
    assert FOUND_PLACEHOLDER_MSG.format(
        filename=path,
        line=1,
        column=19,
        placeholder="__DOMAIN__",
    ) in out


def test_all_matches_across_files_found(test_file, placeholders_file, capsys):
    """Test that check_files reports all unreplaced placeholders in all files."""
    placeholders = placeholders_file("AWS_REGION\nDOMAIN\n")
    path1 = test_file("values.yaml", "aws_region: $AWS_REGION\n")
    path2 = test_file("prod.tfvars", 'route53_domain = "__DOMAIN__"\n')

    exit_code = check_files(
        [path1, path2],
        placeholders,
        [
            r"\${variable}",
            r"__{variable}__",
        ],
    )
    assert exit_code == 1

    out, _ = capsys.readouterr()
    assert FOUND_PLACEHOLDER_MSG.format(
        filename=path1,
        line=1,
        column=13,
        placeholder="$AWS_REGION",
    ) in out
    assert FOUND_PLACEHOLDER_MSG.format(
        filename=path2,
        line=1,
        column=19,
        placeholder="__DOMAIN__",
    ) in out


def test_kubernetes_mode_ignores_terraform_placeholder(test_file, placeholders_file, capsys):
    """Test that kubernetes-style regex ignores terraform-style placeholders."""
    placeholders = placeholders_file("DOMAIN\n")
    path = test_file("prod.tfvars", 'route53_domain = "__DOMAIN__"\n')

    exit_code = check_files(
        [path],
        placeholders,
        [r"\${variable}"],
    )
    assert exit_code == 0

    out, _ = capsys.readouterr()
    assert out == ""


def test_terraform_mode_ignores_kubernetes_placeholder(test_file, placeholders_file, capsys):
    """Test that terraform-style regex ignores kubernetes-style placeholders."""
    placeholders = placeholders_file("AWS_REGION\n")
    path = test_file("values.yaml", "aws_region: $AWS_REGION\n")

    exit_code = check_files(
        [path],
        placeholders,
        [r"__{variable}__"],
    )
    assert exit_code == 0

    out, _ = capsys.readouterr()
    assert out == ""
