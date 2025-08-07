# `kyverno-test`

## Overview

The conceptual overview and configuration details of the hook are available in
the [shared documentation page](../../../README.md) for the hook collection.

## Development

### Prerequisites

Install [pyenv](https://github.com/pyenv/pyenv#installation) and
[pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv#installation) plugin. Then run:

```
➜ pyenv virtualenv 3.13.5 saritasa-pre-commit-hooks-kyverno-test
➜ pyenv activate saritasa-pre-commit-hooks  # not necessary with shell integration
```

### Dependencies

The project dependencies can be installed by running the following command in
the virtual environment:

```
➜ pip install -r requirements.txt
```

### Testing

To launch the tests, one can run the following command from within the hook directory:

```
➜ pytest -v .
```
