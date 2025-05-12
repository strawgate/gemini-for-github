"""Custom exceptions for Aider client operations."""


class AiderError(Exception):
    """Base class for Aider errors.

    Attributes:
        message: The error message.
    """

    def __init__(self, message: str):
        """Initializes the AiderError.

        Args:
            message: The error message.
        """
        self.message = message
        super().__init__(self.message)


class AiderNoneResultError(AiderError):
    """Error raised when an Aider operation returns a None result unexpectedly.

    This indicates that an Aider command or function was expected to produce
    a meaningful result (e.g., generated code or a response), but it returned
    `None` instead, suggesting a potential issue in the Aider process or
    its output parsing.

    Example:
        >>> # Assuming an Aider client method `run_aider`
        >>> try:
        ...     result = client.run_aider(prompt)
        ...     if result is None:
        ...         raise AiderNoneResultError("Aider returned None result.")
        ... except AiderNoneResultError as e:
        ...     print(f"Aider operation failed: {e}")
    """

    def __init__(self, message: str):
        """Initializes the AiderNoneResultError.

        Args:
            message: The error message.
        """
        super().__init__(message)
