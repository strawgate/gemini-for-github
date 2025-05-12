from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from github import Auth, Github
from github.Repository import Repository

from gemini_for_github.errors.github import (
    GithubClientCommentLimitError,
    GithubClientError,
    GithubClientIssueBodyGetError,
    GithubClientIssueCommentCreateError,
    GithubClientIssueCommentsGetError,
    GithubClientIssueGetError,
    GithubClientPRCommentCreateError,
    GithubClientPRCreateError,
    GithubClientPRDiffGetError,
    GithubClientPRGetError,
    GithubClientPRLimitError,
    GithubClientPRReviewCreateError,
    GithubClientPRReviewLimitError,
    GithubClientRepositoryGetError,
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
            issue_number: The numerical ID of the GitHub issue (optional).
            pull_number: The numerical ID of the GitHub pull request (optional).
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
        except GithubClientError as e:
            logger.exception(f"Error occurred while performing {operation}: {details}")
            raise e from e
        except Exception as e:
            logger.exception(f"Unknown error occurred while {operation}: {details}")
            if exception and issubclass(exception, GithubClientError):
                # Instantiate the provided exception type with the details message
                raise exception(message=details) from e
            else:
                # Raise a generic GithubClientError if no specific exception type is provided or it's not a GithubClientError subclass
                raise GithubClientError(message=details or str(e)) from e

    def get_repository(self) -> Repository:
        """Get the repository."""
        with self.error_handler("getting repository", f"repository id: {self.repo_id}", GithubClientRepositoryGetError):
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
        with self.error_handler("getting default branch", f"repository id: {self.repo_id}", GithubClientPRGetError):
            repository = self.github.get_repo(self.repo_id)
            return repository.default_branch

    def get_branch_from_pr(self) -> str:
        """Get the branch name from a pull request."""
        if self.pull_number is None:
            raise ValueError("pull_number must be set to get branch from PR")
        with self.error_handler("getting branch from pull request", f"pull request number: {self.pull_number}", GithubClientPRGetError):
            repository = self.github.get_repo(self.repo_id)
            return repository.get_pull(self.pull_number).head.ref

    def get_pull_request(self) -> dict[str, Any]:
        """Get a pull request."""
        if self.pull_number is None:
            raise ValueError("pull_number must be set to get a pull request")
        with self.error_handler("getting pull request", f"pull request number: {self.pull_number}", GithubClientPRGetError):
            repository = self.github.get_repo(self.repo_id)
            return repository.get_pull(self.pull_number).raw_data

    def get_pull_request_diff(self) -> str:
        """Get the diff for a pull request.

        Returns:
            String containing the diff
        """
        if self.pull_number is None:
            raise ValueError("pull_number must be set to get pull request diff")
        with self.error_handler("getting pull request diff", f"pull request number: {self.pull_number}", GithubClientPRDiffGetError):
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.get_pull(self.pull_number)
            files = pull_request.get_files()

        return "\n".join(file.patch for file in files)

    def create_pr_review(self, body: str, event: str = "COMMENT") -> bool:
        """Create a review on a pull request.

        Args:
            body: Review body text
            event: Review event type (e.g., "COMMENT", "APPROVE", "REQUEST_CHANGES")

        Returns:
            String containing the review information
        """
        if self.pull_number is None:
            raise ValueError("pull_number must be set to create a PR review")
        if self.pr_review_counter == 1:
            msg = "The model attempted to create more than one pull request review but only one is allowed. Model must stop."
            raise GithubClientPRReviewLimitError(msg)

        with self.error_handler("creating pull request review", f"pull request number: {self.pull_number}", GithubClientPRReviewCreateError):
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.get_pull(self.pull_number)
            pull_request.create_review(body=body, event=event)

        self.pr_review_counter += 1

        return True

    def get_issue_with_comments(self) -> dict[str, Any]:
        """Get an issue title, body, tags, and comments.

        Returns:
            A dictionary containing the issue title, body, tags, and comments.
        """
        if self.issue_number is None:
            raise ValueError("issue_number must be set to get issue with comments")
        with self.error_handler("getting issue", f"issue number: {self.issue_number}", GithubClientIssueGetError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(self.issue_number)
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
        logger.debug(f"Issue {self.issue_number}: {result}")
        return result

    def get_issue_body(self) -> str:
        """Get the body of an issue.

        Returns:
            String containing the issue body
        """
        if self.issue_number is None:
            raise ValueError("issue_number must be set to get issue body")
        with self.error_handler("getting issue body", f"issue number: {self.issue_number}", GithubClientIssueBodyGetError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(self.issue_number)
            response = f"# {issue.title}\n\n{issue.body}"
            logger.debug(f"Issue body for issue {self.issue_number}: {response.strip()}")
            return response.strip()

    def get_issue_comments(self) -> list[dict[str, Any]]:
        """Get all comments on an issue.

        Returns:
            List of dictionaries containing comment information
        """
        if self.issue_number is None:
            raise ValueError("issue_number must be set to get issue comments")
        with self.error_handler("getting issue comments", f"issue number: {self.issue_number}", GithubClientIssueCommentsGetError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(self.issue_number)
            return [comment.raw_data for comment in issue.get_comments()]

    def create_issue_comment(self, body: str) -> bool:
        """Create a comment on an issue.

        Args:
            body: Comment body text.

        Returns:
            A string confirming the comment creation and its ID.
        """
        if self.issue_number is None:
            raise ValueError("issue_number must be set to create an issue comment")
        if self.issue_comment_counter == 1:
            msg = "The model attempted to create more than one comment but only one is allowed. Model must stop."
            raise GithubClientCommentLimitError(msg)

        body_suffix = "\n\nThis is an automated response generated by a GitHub Action."

        with self.error_handler("creating issue comment", f"issue number: {self.issue_number}", GithubClientIssueCommentCreateError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(self.issue_number)
            comment = issue.create_comment(body + body_suffix)

        self.issue_comment_counter += 1

        self.issue_comment_counter += 1

        return True

    def create_pull_request_comment(self, body: str) -> bool:
        """Create a comment on a pull request.

        Args:
            body: Comment body text

        Returns:
            A string confirming the comment creation and its ID.
        """
        if self.pull_number is None:
            raise ValueError("pull_number must be set to create a pull request comment")
        with self.error_handler("creating pull request comment", f"pull request number: {self.pull_number}", GithubClientPRCommentCreateError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(self.pull_number)
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
            raise GithubClientPRLimitError(msg)

        with self.error_handler(
            "creating pull request", f"head branch: {head_branch}, base branch: {base_branch}, title: {title}", GithubClientPRCreateError
        ):
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.create_pull(title=title, body=body, head=head_branch, base=base_branch)
            self.pr_create_counter += 1

        return pull_request.raw_data
