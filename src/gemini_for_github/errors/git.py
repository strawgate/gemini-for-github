"""Custom exceptions for Git client operations."""


class GitClientError(Exception):
    """Base class for Git errors.

    Attributes:
        message: The error message.
    """


class GitBranchExistsError(GitClientError):
    """Error raised when a branch already exists.

    This occurs when attempting to create a new branch with a name
    that is already in use.

    Example:
        >>> # Assuming a Git client method `create_branch`
        >>> existing_branch_name = "feature/my-feature"
        >>> try:
        ...     client.create_branch(existing_branch_name)
        ... except GitBranchExistsError as e:
        ...     print(f"Branch already exists: {e}")
    """


class GitPushError(GitClientError):
    """Error raised when a push fails.

    This can happen due to various reasons, such as authentication issues,
    conflicts, or network problems during a `git push` operation.

    Example:
        >>> # Assuming a Git client method `push`
        >>> try:
        ...     client.push("origin", "main")
        ... except GitPushError as e:
        ...     print(f"Git push failed: {e}")
    """


class GitNewBranchError(GitClientError):
    """Error raised when a new branch cannot be created.

    This might occur if the branch name is invalid, the repository is in
    a detached HEAD state, or other Git-related issues prevent branch creation.

    Example:
        >>> # Assuming a Git client method `create_branch`
        >>> invalid_branch_name = "invalid/name?"
        >>> try:
        ...     client.create_branch(invalid_branch_name)
        ... except GitNewBranchError as e:
        ...     print(f"Failed to create new branch: {e}")
    """


class GitCloneError(GitClientError):
    """Error raised when a repository cannot be cloned.

    This can be due to an incorrect repository URL, network issues,
    or insufficient permissions.

    Example:
        >>> # Assuming a Git client method `clone`
        >>> invalid_repo_url = "https://github.com/nonexistent/repo.git"
        >>> try:
        ...     client.clone(invalid_repo_url, "/tmp/clone_dir")
        ... except GitCloneError as e:
        ...     print(f"Failed to clone repository: {e}")
    """


class GitConfigError(GitClientError):
    """Error raised when git configuration fails.

    This occurs when attempting to set or get Git configuration values
    and the operation fails, possibly due to invalid keys or permissions.

    Example:
        >>> # Assuming a Git client method `set_config`
        >>> try:
        ...     client.set_config("user.name", "Test User")
        ... except GitConfigError as e:
        ...     print(f"Git configuration failed: {e}")
    """
