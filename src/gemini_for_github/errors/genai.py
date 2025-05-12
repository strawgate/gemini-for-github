class GenAIClientError(Exception):
    """Base class for all errors related to the GenAI client."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)


class GenAIToolFunctionNotFoundError(GenAIClientError):
    """Error raised when a tool function is not found."""

class GenAIToolFunctionError(GenAIClientError):
    """Error raised when a tool function fails."""

class GenAITaskFailedError(GenAIClientError):
    """Error raised when a task fails."""

class GenAITaskUnknownStatusError(GenAIClientError):
    """Error raised when a task has an unknown status."""
