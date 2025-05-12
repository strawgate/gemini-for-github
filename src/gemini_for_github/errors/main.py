"""Custom exceptions for the main application logic."""


class MainError(Exception):
    """Base class for all custom exceptions in the main module.

    Attributes:
        message: The error message.
    """

    def __init__(self, message: str):
        """Initializes the MainError.

        Args:
            message: The error message.
        """
        self.message = message
        super().__init__(self.message)


class CommandNotSelectedError(MainError):
    """Exception raised when a command is not selected.

    This typically happens when the application requires a specific command
    to be chosen (e.g., via command-line arguments or user input) but none
    was provided.

    Example:
        >>> # Assuming a CLI application requires a command argument
        >>> import sys
        >>> if len(sys.argv) < 2:
        ...     raise CommandNotSelectedError("No command specified.")
    """


class CommandNotFoundError(MainError):
    """Exception raised when a command is not found.

    This occurs when the user or application specifies a command that
    does not exist or is not recognized by the application's command
    dispatcher.

    Example:
        >>> # Assuming a command dispatcher dictionary
        >>> available_commands = {"run": ..., "test": ...}
        >>> requested_command = "deploy"
        >>> if requested_command not in available_commands:
        ...     raise CommandNotFoundError(f"Command '{requested_command}' not found.")
    """
