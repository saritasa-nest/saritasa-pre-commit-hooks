# `kyverno-test`

## Overview

The hook runs [`kyverno test`](https://kyverno.io/docs/kyverno-cli/usage/test/) on Kyverno
policy tests as a pre-commit check, so a policy cannot be committed with failing tests.

Configuration flags and usage examples are documented on the
[shared documentation page](../../../../README.md#kyverno-test) for the hook collection.

### What it does

On each run the hook performs up to three steps.

**1. Validation (strict mode, on by default).** Before anything is executed, `validator.py`
asserts that the repository matches the hook's assumptions — the point is to fail with a precise
message instead of letting `kyverno test` fail obscurely later. It checks that:

- the policies directory contains only `.yaml` files (except those passed via `--ignore-path`);
- each policy is a Kyverno policy manifest — its `apiVersion` is a well-formed `group/version` in
  the `kyverno.io` or `policies.kyverno.io` group, its `kind` is `Policy`, `ClusterPolicy`, or
  `MutatingPolicy`, its `metadata.name` matches its filename, and its spec declares a non-empty
  `rules` list (or `mutations`, for `MutatingPolicy`);
- the tests directory contains one subdirectory per policy, named after it;
- each test subdirectory holds exactly one test manifest (`kyverno-test.yaml` by default) that is
  a `cli.kyverno.io` `Test`, references its own policy by a relative path inside the policies
  directory, and declares a non-empty `results` list.

Strict mode can be turned off with `--disable-strict-mode`.

**2. Target discovery.** Rather than running the whole suite on every commit, the hook inspects
the staged changes and derives the set of policies to test (`main.py`, `_find_targets`):

- a policy that was added or changed selects its own test;
- a file added, changed, or deleted anywhere under a test subdirectory selects that test;
- a policy that was deleted deselects its test, so removing a policy together with its test is
  not an error.

**3. Execution.** For each target, `kyverno test` is invoked on the test subdirectory with
`--require-tests --detailed-results --fail-only`, plus anything given via `--extra-args`. Output
is captured and scanned rather than only checked by exit code, because Kyverno exits zero on some
errors (an unmarshaling error in a test manifest, for instance). By default `WARNING:` in the
output also fails the hook; `--disable-fail-on-warnings` relaxes that.

Any failure prints the captured Kyverno output and exits `1`.

### Expected layout

```
config/
├── policies/
│   ├── kustomization.yaml           # ignorable via --ignore-path
│   └── add-emptydir-sizelimit.yaml  # metadata.name == add-emptydir-sizelimit
└── tests/
    └── add-emptydir-sizelimit/      # named after the policy
        ├── kyverno-test.yaml        # references ../../policies/add-emptydir-sizelimit.yaml
        └── resource.yaml
```

> [!IMPORTANT]
> The CLI tool for Kyverno must be available locally, otherwise the hook fails with a validation
> error. See the [installation documentation](https://kyverno.io/docs/kyverno-cli/install/).

## Development

### Prerequisites

Set up the shared development environment as described in the
[Local development](../../../../README.md#local-development) section of the collection README.
The hook's own dependencies (`pytest`, `pyyaml`) come from `requirements.txt` in this directory:

```console
uv pip install -r pre_commit_hooks/kubernetes/kyverno/kyverno_test/requirements.txt
```

The `kyverno` binary must also be on `PATH`, since `test_run_on_correct_policy` and
`test_run_on_incorrect_policy` shell out to it. On macOS:

```console
brew install kyverno
```

### Testing

Run the hook's tests from the **repository root**, so that the `pre_commit_hooks` package the
tests import can be resolved:

```console
pytest pre_commit_hooks/kubernetes/kyverno/kyverno_test
```

Useful variations:

```console
pytest pre_commit_hooks/kubernetes/kyverno/kyverno_test -v                  # list each test by name
pytest pre_commit_hooks/kubernetes/kyverno/kyverno_test -k mutating         # only matching tests
pytest pre_commit_hooks/kubernetes/kyverno/kyverno_test --collect-only -q   # names, without running
```

To run the whole collection's suite, use `pytest` with no arguments.

### Test layout

`tests/test_hook.py` covers three groups of behaviour: pure path handling (`_get_policy_name`,
`_get_test_directory_name`), target discovery against a throwaway Git repository built by the
`temp_git_dir` fixture, and validator/end-to-end cases driven by the fixtures under
`tests/assets/`.

Each asset directory is a miniature repository (`<asset>/config/policies`, `<asset>/config/tests`)
copied into the temporary Git repository by `_prepare_assets`. To add a case, create an asset that
exhibits the condition and assert on the resulting `ValidationError` message.

> [!NOTE]
> Git cannot track an empty directory. If a case depends on a directory existing, put a file in
> it — an empty file is enough where the assertion fires before the file is read.
