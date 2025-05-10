from typing import Any

from github import Auth, Github


class GitHubAPIClient:
    """Concrete implementation of GitHub API client using PyGithub."""

    def __init__(self, token: str, owner: str, repo: str):
        """Initialize the GitHub API client.

        Args:
            token: GitHub API token for authentication
        """
        auth = Auth.Token(token)
        self.github = Github(auth=auth)
        self.owner = owner
        self.repo = repo

    def get_pull_request_diff(self, pull_number: int) -> str:
        """Get the diff for a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number

        Returns:
            String containing the diff
        """
        repository = self.github.get_repo(f"{self.owner}/{self.repo}")
        pull_request = repository.get_pull(pull_number)
        files = pull_request.get_files()
        return "\n".join(file.patch for file in files)

    def create_pr_review(self, pull_number: int, body: str, event: str = "COMMENT") -> dict[str, Any]:
        """Create a review on a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number
            body: Review body text
            event: Review event type (e.g., "COMMENT", "APPROVE", "REQUEST_CHANGES")

        Returns:
            Dictionary containing the review information
        """
        repository = self.github.get_repo(f"{self.owner}/{self.repo}")
        pull_request = repository.get_pull(pull_number)
        review = pull_request.create_review(body=body, event=event)
        return review.raw_data

    def get_issue_body(self, issue_number: int) -> str:
        """Get the body of an issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            String containing the issue body
        """
        repository = self.github.get_repo(f"{self.owner}/{self.repo}")
        issue = repository.get_issue(issue_number)
        return issue.body or ""

    def get_issue_comments(self, issue_number: int) -> list[dict[str, Any]]:
        """Get all comments on an issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            List of dictionaries containing comment information
        """
        repository = self.github.get_repo(f"{self.owner}/{self.repo}")
        issue = repository.get_issue(issue_number)
        return [comment.raw_data for comment in issue.get_comments()]

    def create_issue_comment(self, issue_number: int, body: str) -> dict[str, Any]:
        """Create a comment on an issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            body: Comment body text

        Returns:
            Dictionary containing the comment information
        """
        repository = self.github.get_repo(f"{self.owner}/{self.repo}")
        issue = repository.get_issue(issue_number)
        comment = issue.create_comment(body)
        return comment.raw_data

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
        repository = self.github.get_repo(f"{self.owner}/{self.repo}")
        pull_request = repository.create_pull(title=title, body=body, head=head_branch, base=base_branch)
        return pull_request.raw_data
