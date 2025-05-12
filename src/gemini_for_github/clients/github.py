from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from github import Auth, Github
from github.Repository import Repository

from gemini_for_github.errors.github import (
    GeminiGithubClientCommentLimitError,
    GeminiGithubClientError,
    GeminiGithubClientIssueBodyGetError,
    GeminiGithubClientIssueCommentCreateError,
    GeminiGithubClientIssueCommentsGetError,
    GeminiGithubClientIssueGetError,
    GeminiGithubClientPRCommentCreateError,
    GeminiGithubClientPRCreateError,
    GeminiGithubClientPRDiffGetError,
    GeminiGithubClientPRGetError,
    GeminiGithubClientPRLimitError,
    GeminiGithubClientPRReviewCreateError,
    GeminiGithubClientPRReviewLimitError,
    GeminiGithubClientRepositoryGetError,
)
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("github")


class GitHubAPIClient:
    """
    A client for interacting with the GitHub API using the PyGithub library.
    It provides methods for accessing repository information, managing issues,
    pull requests, and comments.
    """

    def __init__(self, token: str, repo_id: int, issue_number: int | None = None, pull_number: int | None = None):
        """Initialize the GitHub API client.

        Args:
            token: GitHub API token for authentication.
            repo_id: The numerical ID of the GitHub repository.
            issue_number: Optional default issue number to use for operations.
            pull_number: Optional default pull request number to use for operations.
        """
        auth = Auth.Token(token)
        self.github = Github(auth=auth)
        self.repo_id: int = repo_id
        self.issue_number: int | None = issue_number
        self.pull_number: int | None = pull_number

        self.issue_comment_counter: int = 0
        self.pr_create_counter: int = 0
        self.pr_review_counter: int = 0
        self.issue_create_counter: int = 0

    @contextmanager
    def error_handler(self, operation: str, details: str, exception: type[Exception] | None = None):
        """
        A context manager for handling common GitHub API errors.
        It wraps GitHub API operations and raises specific GithubClientError
        subclasses for known issues, or a generic GithubClientError for unknown exceptions.

        Args:
            operation: The operation being performed, used for logging.
            details: A descriptive message for the generic GithubClientError.
        """
        try:
            logger.info(f"Performing {operation} for {details}")
            yield self.github
            logger.info(f"Successfully performed {operation} for {details}")
        except Exception as e:
            logger.exception(f"Unknown error occurred while {operation}: {details}")
            if exception:
                raise e  # noqa: TRY201
            raise GeminiGithubClientError(message=details or str(e)) from e

    def get_repository(self) -> Repository:
        """Get the repository."""
        with self.error_handler("getting repository", f"repository id: {self.repo_id}", GeminiGithubClientRepositoryGetError):
            return self.github.get_repo(self.repo_id)

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the GitHub API client."""
        return {
            "get_pull_request_diff": self.get_pull_request_diff,
            "create_pr_review": self.create_pr_review,
            "get_pull_request": self.get_pull_request,
            "get_issue_with_comments": self.get_issue_with_comments,
            "create_issue_comment": self.create_issue_comment,
            "create_pull_request": self.create_pull_request,
            "create_pull_request_comment": self.create_pull_request_comment,
            "search_issues": self.search_issues,
        }

    def get_default_branch(self) -> str:
        """Get the default branch for the repository."""
        with self.error_handler("getting default branch", f"repository id: {self.repo_id}", GeminiGithubClientPRGetError):
            repository = self.github.get_repo(self.repo_id)
            return repository.default_branch

    def get_branch_from_pr(self, pull_number: int) -> str:
        """Get the branch name from a pull request."""
        with self.error_handler("getting branch from pull request", f"pull request number: {pull_number}", GeminiGithubClientPRGetError):
            repository = self.github.get_repo(self.repo_id)
            return repository.get_pull(pull_number).head.ref

    def get_pull_request(self, pull_number: int) -> dict[str, Any]:
        """Get a pull request."""
        with self.error_handler("getting pull request", f"pull request number: {pull_number}", GeminiGithubClientPRGetError):
            repository = self.github.get_repo(self.repo_id)
            return repository.get_pull(pull_number).raw_data

    def get_pull_request_diff(self, pull_number: int | None = None) -> str:
        """Get the diff for a pull request.

        Args:
            pull_number: Optional pull request number. Uses the instance's default if None.

        Returns:
            String containing the diff
        """
        pr_num = pull_number if pull_number is not None else self.pull_number
        if pr_num is None:
            raise ValueError("Pull request number must be provided or set in the client.")

        with self.error_handler("getting pull request diff", f"pull request number: {pr_num}", GeminiGithubClientPRDiffGetError):
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.get_pull(pr_num)
            files = pull_request.get_files()

        return "\n".join(file.patch for file in files)

    def create_pr_review(self, body: str, pull_number: int | None = None, event: str = "COMMENT") -> bool:
        """Create a review on a pull request.

        Args:
            body: Review body text
            pull_number: Optional pull request number. Uses the instance's default if None.
            event: Review event type (e.g., "COMMENT", "APPROVE", "REQUEST_CHANGES")

        Returns:
            String containing the review information
        """
        pr_num = pull_number if pull_number is not None else self.pull_number
        if pr_num is None:
            raise ValueError("Pull request number must be provided or set in the client.")

        if self.pr_review_counter == 1:
            msg = "The model attempted to create more than one pull request review but only one is allowed. Model must stop."
            raise GeminiGithubClientPRReviewLimitError(msg)

        with self.error_handler(
            "creating pull request review", f"pull request number: {pr_num}", GeminiGithubClientPRReviewCreateError
        ):
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.get_pull(pr_num)
            pull_request.create_review(body=body, event=event)

        self.pr_review_counter += 1

        return True

    def get_issue_with_comments(self, issue_number: int | None = None) -> dict[str, Any]:
        """Get an issue title, body, tags, and comments.

        Args:
            issue_number: Optional issue number. Uses the instance's default if None.

        Returns:
            A dictionary containing the issue title, body, tags, and comments.
        """
        issue_num = issue_number if issue_number is not None else self.issue_number
        if issue_num is None:
            raise ValueError("Issue number must be provided or set in the client.")

        with self.error_handler("getting issue", f"issue number: {issue_num}", GeminiGithubClientIssueGetError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_num)
            result = {
                "title": issue.title,
                "body": issue.body,
                "tags": [label.name for label in issue.labels],
                "comments": [
                    {
                        "body": comment.body,
                        "author": comment.user.login,
                        "created_at": comment.created_at,
                    }
                    for comment in issue.get_comments()
                ],
            }
        logger.debug(f"Issue {issue_num}: {result}")
        return result

    def get_issue_body(self, issue_number: int | None = None) -> str:
        """Get the body of an issue.

        Args:
            issue_number: Optional issue number. Uses the instance's default if None.

        Returns:
            String containing the issue body
        """
        issue_num = issue_number if issue_number is not None else self.issue_number
        if issue_num is None:
            raise ValueError("Issue number must be provided or set in the client.")

        with self.error_handler("getting issue body", f"issue number: {issue_num}", GeminiGithubClientIssueBodyGetError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_num)
            response = f"# {issue.title}\n\n{issue.body}"
            logger.debug(f"Issue body for issue {issue_num}: {response.strip()}")
            return response.strip()

    def get_issue_comments(self, issue_number: int | None = None) -> list[dict[str, Any]]:
        """Get all comments on an issue.

        Args:
            issue_number: Optional issue number. Uses the instance's default if None.

        Returns:
            List of dictionaries containing comment information
        """
        issue_num = issue_number if issue_number is not None else self.issue_number
        if issue_num is None:
            raise ValueError("Issue number must be provided or set in the client.")

        with self.error_handler("getting issue comments", f"issue number: {issue_num}", GeminiGithubClientIssueCommentsGetError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_num)
            return [comment.raw_data for comment in issue.get_comments()]

    def create_issue_comment(self, body: str, issue_number: int | None = None) -> bool:
        """Create a comment on an issue.

        Args:
            body: Comment body text.
            issue_number: Optional issue number. Uses the instance's default if None.

        Returns:
            A string confirming the comment creation and its ID.
        """
        issue_num = issue_number if issue_number is not None else self.issue_number
        if issue_num is None:
            raise ValueError("Issue number must be provided or set in the client.")

        if self.issue_comment_counter == 1:
            msg = "The model attempted to create more than one comment but only one is allowed. Model must stop."
            raise GeminiGithubClientCommentLimitError(msg)

        body_suffix = "\n\nThis is an automated response generated by a GitHub Action."

        with self.error_handler("creating issue comment", f"issue number: {issue_num}", GeminiGithubClientIssueCommentCreateError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_num)
            comment = issue.create_comment(body + body_suffix)

        self.issue_comment_counter += 1

        return True

    def create_pull_request_comment(self, body: str, pull_number: int | None = None) -> bool:
        """Create a comment on a pull request.

        Args:
            body: Comment body text
            pull_number: Optional pull request number. Uses the instance's default if None.

        Returns:
            A string confirming the comment creation and its ID.
        """
        pr_num = pull_number if pull_number is not None else self.pull_number
        if pr_num is None:
            raise ValueError("Pull request number must be provided or set in the client.")

        with self.error_handler(
            "creating pull request comment", f"pull request number: {pr_num}", GeminiGithubClientPRCommentCreateError
        ):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(pr_num)
            issue.create_comment(body)

        return True

    def search_issues(self, query: str, owner: str, repo: str) -> list[dict[str, Any]]:
        """Search for issues using the GitHub Search API.

        Args:
            query: The search query string.
            owner: The owner of the repository.
            repo: The name of the repository.

        Returns:
            A list of dictionaries containing issue information.
        """
        full_query = f"{query} repo:{owner}/{repo}"
        logger.info(f"Searching issues with query: {full_query}")
        # PyGithub's search_issues returns a PaginatedList, convert to list of dicts
        issues = self.github.search_issues(query=full_query)
        return [issue.raw_data for issue in issues]

    def create_pull_request(self, head_branch: str, base_branch: str, title: str, body: str) -> dict[str, Any]:
        """Create a pull request using PyGithub.

        Args:
            head_branch: The name of the branch where the changes were made.
            base_branch: The name of the branch to merge the changes into.
            title: The title of the pull request.
            body: The body description of the pull request.

        Returns:
            A dictionary containing information about the created pull request.
        """
        if self.pr_create_counter == 1:
            msg = "The model attempted to create more than one pull request but only one is allowed. Stop."
            raise GeminiGithubClientPRLimitError(msg)

        with self.error_handler(
            "creating pull request",
            f"head branch: {head_branch}, base branch: {base_branch}, title: {title}",
            GeminiGithubClientPRCreateError,
        ):
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.create_pull(title=title, body=body, head=head_branch, base=base_branch)
            self.pr_create_counter += 1

        return pull_request.raw_data
