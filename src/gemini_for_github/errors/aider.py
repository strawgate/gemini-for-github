"""Custom exceptions for Aider client operations."""


class AiderError(Exception):
    """
    A custom exception for Aider errors.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class AiderNoneResultError(AiderError):
    """
    A custom exception for Aider errors when the result is None.
    """

    def __init__(self, message: str):
        super().__init__(message)
