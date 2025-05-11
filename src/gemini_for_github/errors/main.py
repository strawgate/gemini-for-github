class MainError(Exception):
    """Base class for all custom exceptions in the main module."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class CommandNotSelectedError(MainError):
    """Exception raised when a command is not selected."""


class CommandNotFoundError(MainError):
    """Exception raised when a command is not found."""
