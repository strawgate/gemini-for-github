"""Custom exceptions for GitHub API client operations."""


class GeminiGithubClientError(Exception):
    """Base class for all errors related to the GitHub client."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)


class GeminiGithubClientCommentLimitError(GeminiGithubClientError):
    """Error raised when the comment limit is reached."""


class GeminiGithubClientPRLimitError(GeminiGithubClientError):
    """Error raised when the PR limit is reached."""


class GeminiGithubClientIssueLimitError(GeminiGithubClientError):
    """Error raised when the issue limit is reached."""


class GeminiGithubClientPRReviewLimitError(GeminiGithubClientError):
    """Error raised when the PR review limit is reached."""


class GeminiGithubClientPRCreateError(GeminiGithubClientError):
    """Error raised when a PR cannot be created."""


class GeminiGithubClientIssueCommentCreateError(GeminiGithubClientError):
    """Error raised when an issue comment cannot be created."""


class GeminiGithubClientIssueBodyGetError(GeminiGithubClientError):
    """Error raised when an issue body cannot be retrieved."""


class GeminiGithubClientIssueCommentsGetError(GeminiGithubClientError):
    """Error raised when an issue comments cannot be retrieved."""


class GeminiGithubClientPRReviewCreateError(GeminiGithubClientError):
    """Error raised when a PR review cannot be created."""


class GeminiGithubClientPRDiffGetError(GeminiGithubClientError):
    """Error raised when a PR diff cannot be retrieved."""


class GeminiGithubClientRepositoryGetError(GeminiGithubClientError):
    """Error raised when a repository cannot be retrieved."""


class GeminiGithubClientIssueGetError(GeminiGithubClientError):
    """Error raised when an issue cannot be retrieved."""


class GeminiGithubClientPRGetError(GeminiGithubClientError):
    """Error raised when a PR cannot be retrieved."""


class GeminiGithubClientPRCommentCreateError(GeminiGithubClientError):
    """Error raised when a PR comment cannot be created."""
