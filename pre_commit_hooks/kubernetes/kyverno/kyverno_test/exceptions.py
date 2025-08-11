from pathlib import Path


class ValidationError(Exception):
    """Represents a validation error."""


class KyvernoTestError(Exception):
    """Represents a Kyverno test execution error.

    Attributes:
        path: A test path.
        output: An output produced during test execution.
        exit_code: An exit code of the test process.
    """
    path: Path
    output: bytes
    exit_code: int

    def __init__(self, message: str, path: Path, output: bytes, exit_code: int) -> None:
        """Initializes KyvernoTestError.

        Args:
            message: An exception message.
            path: A test path.
            output: An output produced during test execution.
            exit_code: An exit code of the test process.
        """
        super().__init__(message)
        self.path = path
        self.output = output
        self.exit_code = exit_code
