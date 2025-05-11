from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from github import Auth, Github
from github.Repository import Repository
from github.PullRequest import PullRequest
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

    def __init__(self, token: str, repo_id: int):
        """Initialize the GitHub API client.

        Args:
            token: GitHub API token for authentication.
            repo_id: The numerical ID of the GitHub repository.
        """
        auth = Auth.Token(token)
        self.github = Github(auth=auth)
        self.repo_id: int = repo_id

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
            if exception:
                raise exception from e
            raise GithubClientError(details) from e

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

    def get_pull_request(self, pull_number: int) -> dict[str, Any]:
        """Get a pull request."""
        with self.error_handler("getting pull request", f"pull request number: {pull_number}", GithubClientPRGetError):
            repository = self.github.get_repo(self.repo_id)
            return repository.get_pull(pull_number).raw_data

    def get_pull_request_diff(self, pull_number: int) -> str:
        """Get the diff for a pull request.

        Args:
            pull_number: Pull request number

        Returns:
            String containing the diff
        """
        with self.error_handler("getting pull request diff", f"pull request number: {pull_number}", GithubClientPRDiffGetError):
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.get_pull(pull_number)
            files = pull_request.get_files()

        return "\n".join(file.patch for file in files)

    def create_pr_review(self, pull_number: int, body: str, event: str = "COMMENT") -> bool:
        """Create a review on a pull request.

        Args:
            pull_number: Pull request number
            body: Review body text
            event: Review event type (e.g., "COMMENT", "APPROVE", "REQUEST_CHANGES")

        Returns:
            String containing the review information
        """
        if self.pr_review_counter == 1:
            msg = "The model attempted to create more than one pull request review but only one is allowed. Model must stop."
            raise GithubClientPRReviewLimitError(msg)

        with self.error_handler("creating pull request review", f"pull request number: {pull_number}", GithubClientPRReviewCreateError):
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.get_pull(pull_number)
            pull_request.create_review(body=body, event=event)

        self.pr_review_counter += 1

        return True

    def get_issue_with_comments(self, issue_number: int) -> dict[str, Any]:
        """Get an issue title, body, tags, and comments.

        Args:
            issue_number: The number of the issue to get.

        Returns:
            A dictionary containing the issue title, body, tags, and comments.
        """
        with self.error_handler("getting issue", f"issue number: {issue_number}", GithubClientIssueGetError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_number)
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
        logger.debug(f"Issue {issue_number}: {result}")
        return result

    def get_issue_body(self, issue_number: int) -> str:
        """Get the body of an issue.

        Args:
            issue_number: Issue number

        Returns:
            String containing the issue body
        """
        with self.error_handler("getting issue body", f"issue number: {issue_number}", GithubClientIssueBodyGetError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_number)
            response = f"# {issue.title}\n\n{issue.body}"
            logger.debug(f"Issue body for issue {issue_number}: {response.strip()}")
            return response.strip()

    def get_issue_comments(self, issue_number: int) -> list[dict[str, Any]]:
        """Get all comments on an issue.

        Args:
            issue_number: Issue number

        Returns:
            List of dictionaries containing comment information
        """
        with self.error_handler("getting issue comments", f"issue number: {issue_number}", GithubClientIssueCommentsGetError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_number)
            return [comment.raw_data for comment in issue.get_comments()]

    def create_issue_comment(self, issue_number: int, body: str) -> bool:
        """Create a comment on an issue.

        Args:
            issue_number: Issue number.
            body: Comment body text.

        Returns:
            A string confirming the comment creation and its ID.
        """
        if self.issue_comment_counter == 1:
            msg = "The model attempted to create more than one comment but only one is allowed. Model must stop."
            raise GithubClientCommentLimitError(msg)

        body_suffix = "\n\nThis is an automated response generated by a GitHub Action."

        with self.error_handler("creating issue comment", f"issue number: {issue_number}", GithubClientIssueCommentCreateError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_number)
            comment = issue.create_comment(body + body_suffix)

        self.issue_comment_counter += 1

        self.issue_comment_counter += 1

        return True

    def create_pull_request_comment(self, pull_number: int, body: str) -> bool:
        """Create a comment on a pull request.

        Args:
            pull_number: Pull request number
            body: Comment body text

        Returns:
            A string confirming the comment creation and its ID.
        """
        with self.error_handler("creating pull request comment", f"pull request number: {pull_number}", GithubClientPRCommentCreateError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(pull_number)
            issue.create_comment(body)

        return True

    def search_issues(self, query: str) -> list[dict[str, Any]]:
        """Searches for issues in the repository.

        Args:
            query: The search query string.

        Returns:
            A list of dictionaries containing information about the found issues.
        """
        with self.error_handler("searching issues", f"query: {query}", GithubClientIssueSearchError):
            # PyGithub's search_issues method searches across all repositories the authenticated user has access to
            # To search within a specific repository, we need to include the repo in the query string
            repo = self.github.get_repo(self.repo_id)
            search_query = f"{query} repo:{repo.owner.login}/{repo.name}"
            issues = self.github.search_issues(query=search_query)
            # Convert the PaginatedList of Issues to a list of dictionaries
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
