from collections.abc import Callable
from typing import Any

from github import Auth, Github
from github.Repository import Repository

from gemini_for_github.errors.github import (
    GithubClientCommentLimitError,
    GithubClientIssueBodyGetError,
    GithubClientIssueCommentCreateError,
    GithubClientIssueCommentsGetError,
    GithubClientPRCreateError,
    GithubClientPRDiffGetError,
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

    def get_repository(self) -> Repository:
        """Get the repository."""
        logger.info(f"Getting repository {self.repo_id}")
        try:
            return self.github.get_repo(self.repo_id)
        except Exception as e:
            msg = f"Error getting repository: {e}"
            logger.exception(msg)
            raise GithubClientRepositoryGetError(msg) from e

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the GitHub API client."""
        return {
            "get_pull_request_diff": self.get_pull_request_diff,
            "create_pr_review": self.create_pr_review,
            "get_issue_body": self.get_issue_body,
            "get_issue_comments": self.get_issue_comments,
            "create_issue_comment": self.create_issue_comment,
            "create_pull_request": self.create_pull_request,
        }

    def get_pull_request_diff(self, pull_number: int) -> str:
        """Get the diff for a pull request.

        Args:
            pull_number: Pull request number

        Returns:
            String containing the diff
        """
        logger.info(f"Getting pull request diff for GitHub PR {pull_number}")
        try:
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.get_pull(pull_number)
            files = pull_request.get_files()

        except Exception as e:
            msg = f"Error getting pull request diff: {e}"
            logger.exception(msg)
            raise GithubClientPRDiffGetError(msg) from e

        return "\n".join(file.patch for file in files)

    def create_pr_review(self, pull_number: int, body: str, event: str = "COMMENT") -> str:
        """Create a review on a pull request.

        Args:
            pull_number: Pull request number
            body: Review body text
            event: Review event type (e.g., "COMMENT", "APPROVE", "REQUEST_CHANGES")

        Returns:
            String containing the review information
        """
        logger.info(f"Creating pull request review for GitHub PR {pull_number}")
        if self.pr_review_counter == 1:
            msg = "The model attempted to create more than one pull request review but only one is allowed. Stop."
            raise GithubClientPRReviewLimitError(msg)

        self.pr_review_counter += 1

        try:
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.get_pull(pull_number)
            review = pull_request.create_review(body=body, event=event)

        except Exception as e:
            msg = f"Error creating pull request review: {e}"
            logger.exception(msg)
            raise GithubClientPRReviewCreateError(msg) from e

        return f"Created review on GitHub PR {pull_number} with id {review.id}"

    def get_issue_body(self, issue_number: int) -> str:
        """Get the body of an issue.

        Args:
            issue_number: Issue number

        Returns:
            String containing the issue body
        """
        logger.info(f"Getting issue body for GitHub issue {issue_number}")
        try:
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_number)
            response = f"# {issue.title}\n\n{issue.body}"
            logger.debug(f"Issue body for issue {issue_number}: {response.strip()}")
            return response.strip()
        except Exception as e:
            msg = f"Error getting issue body: {e}"
            logger.exception(msg)
            raise GithubClientIssueBodyGetError(msg) from e


    def get_issue_comments(self, issue_number: int) -> list[dict[str, Any]]:
        """Get all comments on an issue.

        Args:
            issue_number: Issue number

        Returns:
            List of dictionaries containing comment information
        """
        logger.info(f"Getting issue comments for GitHub issue {issue_number}")
        try:
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_number)
            response = [comment.raw_data for comment in issue.get_comments()]
        except Exception as e:
            msg = f"Error getting issue comments: {e}"
            logger.exception(msg)
            raise GithubClientIssueCommentsGetError(msg) from e

        logger.debug(f"Comments from issue {issue_number}: {response}")
        return response

    def create_issue_comment(self, issue_number: int, body: str) -> str:
        """Create a comment on an issue.

        Args:
            issue_number: Issue number.
            body: Comment body text.

        Returns:
            A string confirming the comment creation and its ID.
        """
        logger.info(f"Creating issue comment for GitHub issue {issue_number}")
        body_suffix = "\n\nThis is an automated response generated by a GitHub Action."

        if self.issue_comment_counter == 1:
            msg = "The model attempted to create more than one comment but only one is allowed. Stop."
            logger.error(msg)
            raise GithubClientCommentLimitError(msg)

        self.issue_comment_counter += 1

        try:
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_number)
            comment = issue.create_comment(body + body_suffix)
        except Exception as e:
            msg = f"Error creating issue comment: {e}"
            logger.exception(msg)
            raise GithubClientIssueCommentCreateError(msg) from e

        return f"Comment {comment.id} created on GitHub issue {issue_number}"

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
        logger.info(f"Creating pull request for GitHub branch {head_branch} into {base_branch} with title {title}")
        if self.pr_create_counter == 1:
            msg = "The model attempted to create more than one pull request but only one is allowed. Stop."
            raise GithubClientPRLimitError(msg)

        try:
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.create_pull(title=title, body=body, head=head_branch, base=base_branch)
            self.pr_create_counter += 1

        except Exception as e:
            msg = f"Error creating pull request: {e}"
            logger.exception(msg)
            raise GithubClientPRCreateError(msg) from e

        return pull_request.raw_data
