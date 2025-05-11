"""Custom exceptions for GitHub API client operations."""


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


class GithubClientPRCreateError(GithubClientError):
    """Error raised when a PR cannot be created."""


class GithubClientIssueCommentCreateError(GithubClientError):
    """Error raised when an issue comment cannot be created."""


class GithubClientIssueBodyGetError(GithubClientError):
    """Error raised when an issue body cannot be retrieved."""


class GithubClientIssueCommentsGetError(GithubClientError):
    """Error raised when an issue comments cannot be retrieved."""


class GithubClientPRReviewCreateError(GithubClientError):
    """Error raised when a PR review cannot be created."""


class GithubClientPRDiffGetError(GithubClientError):
    """Error raised when a PR diff cannot be retrieved."""


class GithubClientRepositoryGetError(GithubClientError):
    """Error raised when a repository cannot be retrieved."""


class GithubClientIssueGetError(GithubClientError):
    """Error raised when an issue cannot be retrieved."""


class GithubClientPRGetError(GithubClientError):
    """Error raised when a PR cannot be retrieved."""


class GithubClientPRCommentCreateError(GithubClientError):
    """Error raised when a PR comment cannot be created."""
