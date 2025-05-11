"""Custom exceptions for Git client operations."""


class GitClientError(Exception):
    """Base class for Git errors."""


class GitBranchExistsError(GitClientError):
    """Error raised when a branch already exists."""


class GitPushError(GitClientError):
    """Error raised when a push fails."""


class GitNewBranchError(GitClientError):
    """Error raised when a new branch cannot be created."""


class GitCloneError(GitClientError):
    """Error raised when a repository cannot be cloned."""


class GitConfigError(GitClientError):
    """Error raised when git configuration fails."""
