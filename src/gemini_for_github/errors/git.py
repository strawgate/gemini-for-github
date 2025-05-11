class GitError(Exception):
    """Base class for Git errors."""


class GitBranchExistsError(GitError):
    """Error raised when a branch already exists."""
