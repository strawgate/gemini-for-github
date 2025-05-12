"""Custom exceptions for Filesystem client operations."""


class FilesystemError(Exception):
    """Base class for all filesystem errors.

    Attributes:
        message: The error message.
    """

    def __init__(self, message: str):
        """Initializes the FilesystemError.

        Args:
            message: The error message.
        """
        self.message = message
        super().__init__(self.message)


class FilesystemNotFoundError(FilesystemError):
    """Error raised when a file or directory is not found.

    This exception is raised when an operation is attempted on a file
    or directory path that does not exist.

    Example:
        >>> from pathlib import Path
        >>> non_existent_file = Path("/tmp/non_existent_file.txt")
        >>> if not non_existent_file.exists():
        ...     raise FilesystemNotFoundError(f"File not found: {non_existent_file}")
    """


class FilesystemReadError(FilesystemError):
    """Error raised when a file cannot be read.

    This can occur due to permission issues, the file being locked,
    or other I/O errors during a read operation.

    Example:
        >>> try:
        ...     with open("/path/to/unreadable_file.txt", "r") as f:
        ...         content = f.read()
        ... except IOError as e:
        ...     raise FilesystemReadError(f"Failed to read file: {e}")
    """


class FilesystemOutsideRootError(FilesystemError):
    """Error raised when a file is outside the root directory.

    This exception is used to prevent operations on paths that are
    not within a designated root directory, often for security reasons.

    Example:
        >>> root = "/app/data"
        >>> malicious_path = "/app/../secrets/config.txt"
        >>> import os
        >>> absolute_path = os.path.abspath(os.path.join(root, malicious_path))
        >>> if not absolute_path.startswith(os.path.abspath(root)):
        ...     raise FilesystemOutsideRootError(f"Path is outside root directory: {malicious_path}")
    """
