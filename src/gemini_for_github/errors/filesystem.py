class FilesystemError(Exception):
    """Base class for all filesystem errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class FilesystemNotFoundError(FilesystemError):
    """Error raised when a file or directory is not found."""


class FilesystemReadError(FilesystemError):
    """Error raised when a file cannot be read."""


class FilesystemOutsideRootError(FilesystemError):
    """Error raised when a file is outside the root directory."""
