# saritasa-pre-commit-hooks

This repository contains special pre-commit hooks that can be reused for Github workflows.

## Hooks available

### `check-nginx-wide-range`

Prevent commiting of nginx wide range configs without `disabled` locations, i.e.

```
# below you can see the example of `wide` nginx config, because files would be searched
# in `$uri` and `$uri/` directories, which can lead to opening of hidden files to the Internet
location / {
  try_files $uri $uri/ /index.php?$query_string;
}

# hook won't raise errors only if there would be defined all below blocks in nginx config (by default)
location ~ \.(json|sh|xml|md|conf|toml|yml|yaml|log|pid)$  {deny all;}
location ~ /cron.*                                              {deny all;}
location ~ /\.                                                  {deny all;}
location ~ autodiscover.xml {return 403;}
location ~ apple-touch-icon {return 403;}
location ~ ^/(app/|vendor|src|tests|vagrant|docs|phpunit|svn|git|docker|migrations|Makefile) {return 403;}
```

#### Examples

1. You can specify custom nginx config file and location `--nginx_config_path=custom.conf`  in case if it is different from `./nginx.conf`

```yaml
repos:
  - repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
    rev: 0.0.5
    hooks:
      - id: check-nginx-wide-range
        args:
          - --nginx_config_path=ci/custom.conf
```

2. You can specify extra deny locations in addition to default ones if you need to check repo for some extra disabled locations with `--extra_deny_locations="^/(test/|test1|test2)"` param

Examples:

```yaml
repos:
  - repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
    rev: 0.0.5
    hooks:
      - id: check-nginx-wide-range
        args:
          - --extra_deny_locations=^/(test/|test1|test2)
          - --extra_deny_locations=/cron3.*
```

3. You can specify custom deny locations to fully replace default ones if you need to check repo for some other disabled locations with `--custom_deny_locations="/cron2.*"` param

Examples:

```yaml
repos:
  - repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
    rev: 0.0.5
    hooks:
      - id: check-nginx-wide-range
        args:
          - --custom_deny_locations=^/(app/|vendor)
          - --custom_deny_locations=/cron2.*
```

Please keep in mind that in case if you messed default locations denies values, hook will ask you to update it to look the same. I.e. when you mixed order of params in `\.(sh|json|conf|xml|md|conf|toml|yml|yaml|log|pid)$` -> you would be forced to update it to this manner `\.(json|sh|xml|md|conf|toml|yml|yaml|log|pid)$`.

4. You can specify extra keywords, existance of which, will make parser error to be ignored `--ignore_errors_keywords="test"` param

Examples:

```yaml
repos:
  - repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
    rev: 0.0.5
    hooks:
      - id: check-nginx-wide-range
        args:
          - --ignore_errors_keywords=test
          - --ignore_errors_keywords=test2
```

Please note that by default there are always ignored errors with these keywords: `fastcgi_params, koi-utf, koi-win, mime.types, scgi_params, uwsgi_params, win-utf`.

Thiey are ignored because sometimes project's nginx config file may contain `include` directives to files without their real presence in the repo (these files are added as [nginx defaults](https://github.com/nginx/nginx/tree/master/conf) during installation) and can be ignored during pre-commit hook processing.

This is it!

### `add_task_number`

Provide task number to commit automatically. It takes task number from branch's name, so branch should have pre-defined
format in order this hook to work.

#### Examples

Commit message: `My beautiful message`
Branch name: `feature/ABC-123-my-branch`

Then branch name will be parsed according to `branch-regex` argument (`(feature|fix)/(?P<task>[A-Z0-9]+-[0-9]+)-.*` by default) and task number will be retrieved from branch name. In this case task number is `ABC-123`
Then this task number will be automatically appended to commit message according to `format` argument
(`{message}\\n\\nTask: {task}` by default), so result message will be
```
My beautiful message

Task: ABC-123
```

Example of what should be added to `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
    rev: 0.0.5
    hooks:
      - id: add-task-number
        # To check logs about which task was appended to commit message
        verbose: true
        args:
          - "--branch-regex=feature/(?P<task>[A-Z]{2,11}-[0-9]{1,6})-.*"
          - "--format={message}\\n\\nTask: {task}"
```

### `jira-pre-commit`

Prevent committing without Jira Task ID in the commit message.

- Fails the commit if no Jira Task ID (e.g., `JIRA-1234`) is found in the commit message.
- Provides possibility to exclude commits by regex (i.e. to exclude `Merge ` commits)

### Hook usage example

Example of what should be added to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
    rev: 0.0.5
    hooks:
      - id: jira-pre-commit
        verbose: true
        args:
          - --exclude-pattern
          - '^draft: '
          - -e
          - '^wip: '
```

### Examples

#### Valid commit messages:

- `feat: add README.md JIRA-123`
- `chore: fix typo, JIRA-321`
- `docs: add docs Task: JIRA-4321`
- ```
  feat: add tests for multi-line

  Task: JIRA-234
  ```

Such commits result in a passed pre-commit hook and don't output any error message.

#### Invalid commit message:

- `feat: add README.md`
- `chore: fix typo, jira-321`
- `docs: add docs Task: JIRA4321`

Such commits result in a failed pre-commit hook and output below error message:

- **[ERROR] Aborting commit. Your commit message is missing a Jira Task ID, i.e. JIRA-1234.**

For commits generated by `git merge` command (like `Merge branch test into main`), hook ignores Jira task absense and outputs below message:

- **Commit matches exclude pattern '^Merge ', skipping JIRA check**

Commits that match the passed `--exclude-patterns` regex won't trigger the hook with Jira Task absense and output below message:

- **Commit matches exclude pattern '<provided_regex>', skipping JIRA check**

In a case of an invalid regex of a provided pattern (i.e. unclosed brackets), hook will catch an error, fail and output below message with an actual regex error:

- **[ERROR] Invalid regex 'bracket( ': missing ), unterminated subpattern**

### `kyverno-test`

Run tests for Kyverno policies. The hook implements a target discovery mechanism to avoid running
all tests on every commit. The test for a policy will be selected for running if:
- the corresponding policy is added or changed;
- a file related to the policy test is added, changed, or deleted.

> [!IMPORTANT]
> The CLI tool for Kyverno must be available locally.
> Learn about various installation methods in the [documentation](https://kyverno.io/docs/kyverno-cli/install/).

#### Configuration example

The basic configuration for the hook has the following form:

```yaml
repos:
  - repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
    rev: 0.0.5
    hooks:
      - id: kyverno-test
        args:
          - --policies=config/kyverno/policies
          - --tests=config/kyverno/tests
```

With the `--policies` (or `-p`) flag, the path to a directory containing Kyverno policy manifests is
specified. The `--tests` (or `-t`) flag is used to set the path to a directory with policy tests.

The hook assumes that:
- policies directory contains YAML manifests;
- tests directory contains subdirectories for policy tests (one subdirectory for each manifest in policies).

To ignore a file or a subdirectory in policies directory, `--ignore-path` flag can be used, for example:

```yaml
- id: kyverno-test
  args:
    # ...
    - --ignore-path=kustomization.yaml
```

If a custom name is used for Kyverno test manifest (instead of the default `kyverno-test.yaml`), one must
account for that in the hook configuration:

```yaml
- id: kyverno-test
  args:
    # ...
    - --test-filename=pt.yaml
```

It is also possible to specify additional arguments for `kyverno test`:

```yaml
- id: kyverno-test
  args:
    # ...
    - --extra-args=-v=4 --remove-color=true --detailed-results=false
```

By default the hook fails on warnings, this can be disabled by specifying the following flag:

```yaml
- id: kyverno-test
  args:
    # ...
    - --disable-fail-on-warnings
```

By default, the hook is executed in strict mode, which means running a validator to check that
the test environment matches the hook's expectations. To completely disable validation, you can
use the following flag.

```yaml
- id: kyverno-test
  args:
    # ...
    - --disable-strict-mode
```

### `check-placeholders`

Prevent committing files with unreplaced placeholder variables.

The hook checks files passed by pre-commit for placeholder values defined in `placeholders.toml`.

Supported placeholder styles:

- kubernetes style: `$VAR`
- terraform style: `__VAR__`

By default, the hook checks both styles.

If an unreplaced placeholder is found, the hook fails and outputs an error in the format:

```sh
filename:line:column: unreplaced placeholder <placeholder>
```

This format was chosen for convenience, because it becomes "clickable" in VScode, and takes you directly to the matched placeholder (with ctrl + click).

#### Hook usage example

The basic configuration for the hook has the following form:

```yaml
- repo: https://github.com/saritasa-nest/saritasa-pre-commit-hooks
  rev: 0.0.7
  hooks:
    - id: check-placeholders
```

To check only for kubernetes-style placeholders:

```yaml
- id: check-placeholders
  args:
    - --mode=kubernetes
```

To check only for terraform-style placeholders:

```yaml
- id: check-placeholders
  args:
    - --mode=terraform
```

#### Examples

The following example will fail the hook:

```hcl
eks_external_secrets_prefix_access = [
  "__PROJECT_NAME__-staging",
  "__PROJECT_NAME__-dev"
]
```

With the following error:

```sh
terraform/terraform/staging/staging.tfvars:604:6: unreplaced placeholder __PROJECT_NAME__
terraform/terraform/staging/staging.tfvars:605:6: unreplaced placeholder __PROJECT_NAME__
```

The following example will fail the hook:

```yaml
labels:
  created-by: $CREATED_BY
  ops-main: $CREATED_BY
  ops-secondary: $OPS_SECONDARY
```

With the following error:

```sh
kubernetes/prod/argocd/apps/values.yaml:1909:13: unreplaced placeholder $CREATED_BY
kubernetes/prod/argocd/apps/values.yaml:1910:11: unreplaced placeholder $CREATED_BY
kubernetes/prod/argocd/apps/values.yaml:1911:16: unreplaced placeholder $OPS_SECONDARY
```
