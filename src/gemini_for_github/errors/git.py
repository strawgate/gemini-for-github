class GitError(Exception):
    """Base class for Git errors."""


class GitBranchExistsError(GitError):
    """Error raised when a branch already exists."""


class GitPushError(GitError):
    """Error raised when a push fails."""


class GitNewBranchError(GitError):
    """Error raised when a new branch cannot be created."""
