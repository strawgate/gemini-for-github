from src.gemini_for_github.clients.github_api_client import GitHubAPIClient


def get_file_content(github_api: GitHubAPIClient, owner: str, repo: str, path: str) -> str:
    """Get the content of a file from a GitHub repository.

    Args:
        github_api: GitHub API client
        owner: Repository owner
        repo: Repository name
        path: Path to the file

    Returns:
        Content of the file
    """
    return github_api.get_file_content(owner, repo, path)


def get_pull_request_diff(github_api: GitHubAPIClient, pr_number: int) -> str:
    """Get the diff of a pull request.

    Args:
        github_api: GitHub API client
        pr_number: Pull request number

    Returns:
        Diff of the pull request
    """
    return github_api.get_pull_request_diff(pr_number)


def get_issue_body(github_api: GitHubAPIClient, issue_number: int) -> str:
    """Get the body of an issue.

    Args:
        github_api: GitHub API client
        issue_number: Issue number

    Returns:
        Body of the issue
    """
    return github_api.get_issue_body(issue_number)


def create_pr_review(github_api: GitHubAPIClient, pr_number: int, body: str, event: str = "COMMENT") -> None:
    """Create a review on a pull request.

    Args:
        github_api: GitHub API client
        pr_number: Pull request number
        body: Review body
        event: Review event (APPROVE, REQUEST_CHANGES, or COMMENT)
    """
    github_api.create_pr_review(pr_number, body, event)


def create_issue_comment(github_api: GitHubAPIClient, issue_number: int, body: str) -> None:
    """Create a comment on an issue.

    Args:
        github_api: GitHub API client
        issue_number: Issue number
        body: Comment body
    """
    github_api.create_issue_comment(issue_number, body)


def create_github_pull_request(github_api: GitHubAPIClient, head_branch: str, base_branch: str, title: str, body: str) -> dict:
    """Create a pull request on GitHub.

    Args:
        github_api: GitHub API client
        head_branch: The name of the branch where the changes were made (e.g., Aider's new branch).
        base_branch: The name of the branch to merge the changes into (e.g., 'main').
        title: The title of the pull request.
        body: The body description of the pull request.

    Returns:
        A dictionary containing information about the created pull request (e.g., URL, number).
    """
    # Assuming the GitHubAPIClient has a method named create_pull_request
    # This method should handle the actual interaction with the PyGithub library.
    # It should return a dictionary with relevant PR details upon success.
    return github_api.create_pull_request(head_branch, base_branch, title, body)
