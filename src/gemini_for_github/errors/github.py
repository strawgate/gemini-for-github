class GithubClientError(Exception):
    """Base class for all errors related to the GitHub client."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)


class GithubClientCommentLimitError(GithubClientError):
    """Error raised when the comment limit is reached."""


class GithubClientPRLimitError(GithubClientError):
    """Error raised when the PR limit is reached."""


class GithubClientIssueLimitError(GithubClientError):
    """Error raised when the issue limit is reached."""


class GithubClientPRReviewLimitError(GithubClientError):
    """Error raised when the PR review limit is reached."""
