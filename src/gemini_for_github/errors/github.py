"""Custom exceptions for GitHub API client operations."""


class GeminiGithubClientError(Exception):
    """Base class for all errors related to the GitHub client.

    Attributes:
        message: The error message.
    """

    def __init__(self, message: str, *args: object) -> None:
        """Initializes the GeminiGithubClientError.

        Args:
            message: The error message.
            *args: Additional arguments.
        """
        super().__init__(message, *args)


class GeminiGithubClientCommentLimitError(GeminiGithubClientError):
    """Error raised when the comment limit is reached.

    This occurs when the application attempts to create more comments
    (on issues or pull requests) than allowed by GitHub's API rate limits
    or internal application limits.

    Example:
        >>> # Assuming a client method `create_comment`
        >>> try:
        ...     client.create_comment(issue_id, "This is a comment.")
        ... except GeminiGithubClientCommentLimitError as e:
        ...     print(f"Comment limit reached: {e}")
    """


class GeminiGithubClientPRLimitError(GeminiGithubClientError):
    """Error raised when the PR limit is reached.

    This indicates that the application has attempted to create more
    pull requests than allowed by GitHub's API rate limits or internal
    application limits.

    Example:
        >>> # Assuming a client method `create_pull_request`
        >>> try:
        ...     client.create_pull_request(...)
        ... except GeminiGithubClientPRLimitError as e:
        ...     print(f"Pull request limit reached: {e}")
    """


class GeminiGithubClientIssueLimitError(GeminiGithubClientError):
    """Error raised when the issue limit is reached.

    This indicates that the application has attempted to create more
    issues than allowed by GitHub's API rate limits or internal
    application limits.

    Example:
        >>> # Assuming a client method `create_issue`
        >>> try:
        ...     client.create_issue(...)
        ... except GeminiGithubClientIssueLimitError as e:
        ...     print(f"Issue limit reached: {e}")
    """


class GeminiGithubClientPRReviewLimitError(GeminiGithubClientError):
    """Error raised when the PR review limit is reached.

    This occurs when the application attempts to create more pull request
    reviews than allowed by GitHub's API rate limits or internal
    application limits.

    Example:
        >>> # Assuming a client method `create_pr_review`
        >>> try:
        ...     client.create_pr_review(pr_id, "Looks good.")
        ... except GeminiGithubClientPRReviewLimitError as e:
        ...     print(f"PR review limit reached: {e}")
    """


class GeminiGithubClientPRCreateError(GeminiGithubClientError):
    """Error raised when a PR cannot be created.

    This can be due to various reasons, such as invalid branch names,
    no changes between branches, or GitHub API errors during creation.

    Example:
        >>> # Assuming a client method `create_pull_request`
        >>> try:
        ...     client.create_pull_request(title="New Feature", body="...", head="feature", base="main")
        ... except GeminiGithubClientPRCreateError as e:
        ...     print(f"Failed to create pull request: {e}")
    """


class GeminiGithubClientIssueCommentCreateError(GeminiGithubClientError):
    """Error raised when an issue comment cannot be created.

    This might happen due to API errors, invalid issue IDs, or permission issues.

    Example:
        >>> # Assuming a client method `create_issue_comment`
        >>> try:
        ...     client.create_issue_comment(issue_id=123, body="Adding a comment.")
        ... except GeminiGithubClientIssueCommentCreateError as e:
        ...     print(f"Failed to create issue comment: {e}")
    """


class GeminiGithubClientIssueBodyGetError(GeminiGithubClientError):
    """Error raised when an issue body cannot be retrieved.

    This can occur if the issue ID is invalid, the repository is not found,
    or due to GitHub API errors during retrieval.

    Example:
        >>> # Assuming a client method `get_issue_body`
        >>> try:
        ...     body = client.get_issue_body(issue_id=999) # Non-existent issue
        ... except GeminiGithubClientIssueBodyGetError as e:
        ...     print(f"Failed to retrieve issue body: {e}")
    """


class GeminiGithubClientIssueCommentsGetError(GeminiGithubClientError):
    """Error raised when issue comments cannot be retrieved.

    This might happen due to API errors, invalid issue IDs, or permission issues.

    Example:
        >>> # Assuming a client method `get_issue_comments`
        >>> try:
        ...     comments = client.get_issue_comments(issue_id=123)
        ... except GeminiGithubClientIssueCommentsGetError as e:
        ...     print(f"Failed to retrieve issue comments: {e}")
    """


class GeminiGithubClientPRReviewCreateError(GeminiGithubClientError):
    """Error raised when a PR review cannot be created.

    This can be due to API errors, invalid pull request IDs, or permission issues.

    Example:
        >>> # Assuming a client method `create_pr_review`
        >>> try:
        ...     client.create_pr_review(pr_id=456, body="Review comments.")
        ... except GeminiGithubClientPRReviewCreateError as e:
        ...     print(f"Failed to create PR review: {e}")
    """


class GeminiGithubClientPRDiffGetError(GeminiGithubClientError):
    """Error raised when a PR diff cannot be retrieved.

    This might happen due to API errors, invalid pull request IDs, or issues
    with the diff generation on GitHub's side.

    Example:
        >>> # Assuming a client method `get_pr_diff`
        >>> try:
        ...     diff = client.get_pr_diff(pr_id=789)
        ... except GeminiGithubClientPRDiffGetError as e:
        ...     print(f"Failed to retrieve PR diff: {e}")
    """


class GeminiGithubClientRepositoryGetError(GeminiGithubClientError):
    """Error raised when a repository cannot be retrieved.

    This occurs if the repository does not exist, the user lacks permissions,
    or due to GitHub API errors.

    Example:
        >>> # Assuming a client method `get_repository`
        >>> try:
        ...     repo = client.get_repository("nonexistent/repo")
        ... except GeminiGithubClientRepositoryGetError as e:
        ...     print(f"Failed to retrieve repository: {e}")
    """


class GeminiGithubClientIssueGetError(GeminiGithubClientError):
    """Error raised when an issue cannot be retrieved.

    This can occur if the issue ID is invalid, the repository is not found,
    or due to GitHub API errors during retrieval.

    Example:
        >>> # Assuming a client method `get_issue`
        >>> try:
        ...     issue = client.get_issue(issue_id=999) # Non-existent issue
        ... except GeminiGithubClientIssueGetError as e:
        ...     print(f"Failed to retrieve issue: {e}")
    """


class GeminiGithubClientPRGetError(GeminiGithubClientError):
    """Error raised when a PR cannot be retrieved.

    This can occur if the pull request ID is invalid, the repository is not found,
    or due to GitHub API errors during retrieval.

    Example:
        >>> # Assuming a client method `get_pull_request`
        >>> try:
        ...     pr = client.get_pull_request(pr_id=999) # Non-existent PR
        ... except GeminiGithubClientPRGetError as e:
        ...     print(f"Failed to retrieve PR: {e}")
    """


class GeminiGithubClientPRCommentCreateError(GeminiGithubClientError):
    """Error raised when a PR comment cannot be created.

    This might happen due to API errors, invalid pull request IDs, or permission issues.

    Example:
        >>> # Assuming a client method `create_pr_comment`
        >>> try:
        ...     client.create_pr_comment(pr_id=456, body="Adding a PR comment.")
        ... except GeminiGithubClientPRCommentCreateError as e:
        ...     print(f"Failed to create PR comment: {e}")
    """
