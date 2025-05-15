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

    def __init__(self, token: str, repo_id: int, owner_repo: str):
        """Initialize the GitHub API client.

        Args:
            token: GitHub API token for authentication.
            repo_id: The numerical ID of the GitHub repository.
        """
        auth = Auth.Token(token)
        self.github = Github(auth=auth)
        self.repo_id: int = repo_id
        self.owner_repo = owner_repo

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
        """
        Retrieves the PyGithub `Repository` object for the configured `repo_id`.

        Use this if you need direct access to the PyGithub `Repository` object
        for operations not covered by the client's specific tool methods.

        Returns:
            Repository: The PyGithub `Repository` object.

        Raises:
            GeminiGithubClientRepositoryGetError: If the repository cannot be fetched (e.g., invalid ID, permissions).
            GeminiGithubClientError: For other unexpected errors.
        """
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
            "multi_search_issues": self.multi_search_issues,
            "get_issue_body": self.get_issue_body,

        }

    def get_default_branch(self) -> str:
        """
        Retrieves the name of the default branch (e.g., 'main', 'master') for the repository.

        Returns:
            str: The name of the default branch.
                 Example: "main"

        Raises:
            GeminiGithubClientRepositoryGetError: If the repository cannot be fetched.
            GeminiGithubClientError: For other unexpected errors.
        """
        with self.error_handler("getting default branch", f"repository id: {self.repo_id}", GeminiGithubClientPRGetError):
            repository = self.github.get_repo(self.repo_id)
            return repository.default_branch

    def get_branch_from_pr(self, pull_number: int) -> str:
        """
        Retrieves the name of the head branch (the branch containing the changes) for a given pull request.

        Args:
            pull_number (int): The number of the pull request.

        Returns:
            str: The name of the head branch.
                 Example: "feature/new-login"

        Raises:
            GeminiGithubClientPRGetError: If the pull request cannot be fetched (e.g., invalid number, permissions).
            GeminiGithubClientError: For other unexpected errors.
        """
        with self.error_handler("getting branch from pull request", f"pull request number: {pull_number}", GeminiGithubClientPRGetError):
            repository = self.github.get_repo(self.repo_id)
            return repository.get_pull(pull_number).head.ref

    def get_pull_request(self, pull_number: int) -> dict[str, Any]:
        """
        Retrieves the raw data for a specific pull request.

        Use this to get detailed information about a pull request, including its title, body,
        author, state, branches, etc., as provided by the GitHub API.

        Args:
            pull_number (int): The number of the pull request.

        Returns:
            dict[str, Any]: A dictionary representing the raw JSON data of the pull request
                            returned by the GitHub API. The exact structure depends on the API version
                            and response. Consult the GitHub API documentation for details.
                            Example (simplified):
                            ```json
                            {
                              "url": "https://api.github.com/repos/owner/repo/pulls/123",
                              "id": 1,
                              "number": 123,
                              "state": "open",
                              "title": "Add new feature",
                              "user": { "login": "octocat", ... },
                              "body": "This PR implements the feature.",
                              "created_at": "2024-01-01T10:00:00Z",
                              "head": { "ref": "feature-branch", ... },
                              "base": { "ref": "main", ... },
                              ...
                            }
                            ```

        Raises:
            GeminiGithubClientPRGetError: If the pull request cannot be fetched.
            GeminiGithubClientError: For other unexpected errors.
        """
        with self.error_handler("getting pull request", f"pull request number: {pull_number}", GeminiGithubClientPRGetError):
            repository = self.github.get_repo(self.repo_id)
            return repository.get_pull(pull_number).raw_data

    def get_pull_request_diff(self, pull_number: int) -> str:
        """
        Retrieves the combined diff of all file changes included in a pull request.

        Use this tool to get the code changes proposed in a specific pull request,
        formatted as a standard diff string. This is often used as input for code review
        or analysis tasks.

        Args:
            pull_number (int): The number of the pull request.

        Returns:
            str: A string containing the concatenated diffs (`.patch` attribute) for all files
                 in the pull request.
                 Example:
                 ```diff
                 --- a/file1.py
                 +++ b/file1.py
                 @@ -1,1 +1,2 @@
                  print("hello")
                 +print("python")

                 --- a/file2.txt
                 +++ b/file2.txt
                 @@ -1 +1 @@
                 -old line
                 +new line
                 ```

        Raises:
            GeminiGithubClientPRDiffGetError: If the pull request or its files cannot be fetched.
            GeminiGithubClientError: For other unexpected errors.
        """
        with self.error_handler("getting pull request diff", f"pull request number: {pull_number}", GeminiGithubClientPRDiffGetError):
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.get_pull(pull_number)
            files = pull_request.get_files()

        return "\n".join(file.patch for file in files)

    def create_pr_review(self, pull_number: int, body: str, event: str = "COMMENT") -> bool:
        """
        Creates a pull request review with a comment.

        Use this tool to submit feedback on a pull request. It creates a single review
        comment. Note: This client enforces a limit of **one** review creation per instance
        to prevent accidental spamming.

        Args:
            pull_number (int): The number of the pull request to review.
            body (str): The text content of the review comment.
            event (str): The type of review event. Common values are:
                         - "COMMENT": Submit general feedback without explicit approval/rejection. (Default)
                         - "APPROVE": Approve the pull request.
                         - "REQUEST_CHANGES": Request changes on the pull request.

        Returns:
            bool: True if the review was created successfully.

        Raises:
            GeminiGithubClientPRReviewLimitError: If a review has already been created by this client instance.
            GeminiGithubClientPRReviewCreateError: If the review creation fails via the API (e.g., permissions, invalid PR number).
            GeminiGithubClientError: For other unexpected errors.
        """
        if self.pr_review_counter == 1:
            msg = "The model attempted to create more than one pull request review but only one is allowed. Model must stop."
            raise GeminiGithubClientPRReviewLimitError(msg)

        with self.error_handler(
            "creating pull request review", f"pull request number: {pull_number}", GeminiGithubClientPRReviewCreateError
        ):
            repository = self.github.get_repo(self.repo_id)
            pull_request = repository.get_pull(pull_number)
            pull_request.create_review(body=body, event=event)

        self.pr_review_counter += 1

        return True

    def get_issue_with_comments(self, issue_number: int) -> dict[str, Any]:
        """
        Retrieves comprehensive details about a specific issue, including its comments.

        Use this tool to get the title, main description (body), assigned labels (tags),
        and all comments associated with a GitHub issue. This provides full context for
        understanding the issue and its discussion.

        Args:
            issue_number (int): The number of the issue to retrieve.

        Returns:
            A dictionary containing the issue title, body, tags, and comments.
        """
        with self.error_handler("getting issue", f"issue number: {issue_number}", GeminiGithubClientIssueGetError):
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
        """
        Retrieves the title and main body content of a specific issue.

        Use this tool when you only need the primary description of the issue,
        not the comments or other metadata.

        Args:
            issue_number (int): The number of the issue.

        Returns:
            str: A string containing the issue title and body, formatted with
                 the title as a markdown heading.
                 Example:
                 "# Bug in login page\n\nUsers cannot log in with valid credentials."

        Raises:
            GeminiGithubClientIssueBodyGetError: If the issue or its body cannot be fetched.
            GeminiGithubClientError: For other unexpected errors.
        """
        with self.error_handler("getting issue body", f"issue number: {issue_number}", GeminiGithubClientIssueBodyGetError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_number)
            response = f"# {issue.title}\n\n{issue.body}"
            logger.debug(f"Issue body for issue {issue_number}: {response.strip()}")
            return response.strip()

    def get_issue_comments(self, issue_number: int) -> list[dict[str, Any]]:
        """
        Retrieves all comments associated with a specific issue.

        Use this tool when you need the discussion history of an issue, separate from
        its main body.

        Args:
            issue_number (int): The number of the issue.

        Returns:
            list[dict[str, Any]]: A list of dictionaries, where each dictionary represents
                                  the raw data of a single comment as returned by the GitHub API.
                                  Consult the GitHub API documentation for the comment object structure.
                                  Example (simplified):
                                  ```json
                                  [
                                    { "id": 1, "user": { "login": "user1" }, "body": "Comment 1", ... },
                                    { "id": 2, "user": { "login": "user2" }, "body": "Comment 2", ... }
                                  ]
                                  ```

        Raises:
            GeminiGithubClientIssueCommentsGetError: If the issue or its comments cannot be fetched.
            GeminiGithubClientError: For other unexpected errors.
        """
        with self.error_handler("getting issue comments", f"issue number: {issue_number}", GeminiGithubClientIssueCommentsGetError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_number)
            return [comment.raw_data for comment in issue.get_comments()]

    def create_issue_comment(self, issue_number: int, body: str) -> bool:
        """
        Creates a new comment on a specified GitHub issue.

        Use this tool to add a comment to an ongoing issue discussion. A standard suffix
        indicating the comment is automated is appended to the body. Note: This client
        enforces a limit of **one** issue comment creation per instance to prevent
        accidental spamming.

        Args:
            issue_number (int): The number of the issue to comment on.
            body (str): The text content of the comment.

        Returns:
            bool: True if the comment was created successfully.

        Raises:
            GeminiGithubClientCommentLimitError: If a comment has already been created by this client instance.
            GeminiGithubClientIssueCommentCreateError: If the comment creation fails via the API (e.g., permissions, invalid issue number).
            GeminiGithubClientError: For other unexpected errors.
        """
        if self.issue_comment_counter == 1:
            msg = "The model attempted to create more than one comment but only one is allowed. Model must stop."
            raise GeminiGithubClientCommentLimitError(msg)

        body_suffix = "\n\nThis is an automated response generated by a GitHub Action."

        with self.error_handler("creating issue comment", f"issue number: {issue_number}", GeminiGithubClientIssueCommentCreateError):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(issue_number)
            comment = issue.create_comment(body + body_suffix)

        self.issue_comment_counter += 1

        return True

    def create_pull_request_comment(self, pull_number: int, body: str) -> bool:
        """
        Creates a general comment on a specified pull request (not a review comment).

        Use this tool to add a general comment to the pull request conversation thread.
        This is different from creating a review or commenting on specific lines of code.

        Args:
            pull_number (int): The number of the pull request to comment on.
            body (str): The text content of the comment.

        Returns:
            bool: True if the comment was created successfully.

        Raises:
            GeminiGithubClientPRCommentCreateError: If the comment creation fails via the API (e.g., permissions, invalid PR number).
            GeminiGithubClientError: For other unexpected errors.
        """
        with self.error_handler(
            "creating pull request comment", f"pull request number: {pull_number}", GeminiGithubClientPRCommentCreateError
        ):
            repository = self.github.get_repo(self.repo_id)
            issue = repository.get_issue(pull_number)
            issue.create_comment(body)

        return True

    def multi_search_issues(self, queries: list[str]) -> list[dict[str, Any]]:
        """
        Performs many sequential queries against the Github Issues API and returns the results.

        Use this tool to find issues matching specific criteria (keywords, labels, authors, etc.)

        Args:
            queries (list[str]): The search query string, following GitHub's issue search syntax.
                         Example: ["is:open label:bug login error", "is:closed label:feature"]

        Returns:
            list[dict[str, Any]]: A list of dictionaries, where each dictionary represents
                                  the raw data of an issue matching the search query, as
                                  returned by the GitHub API. Consult the GitHub API documentation
                                  for the issue object structure.

        Raises:
            GithubException: If the search API call fails (e.g., rate limiting, invalid query).
            GeminiGithubClientError: For other unexpected errors.
        """
        issues = []

        for query in queries:
            issues.extend(self.search_issues(query))

        return issues


    def search_issues(self, query: str) -> list[dict[str, Any]]:
        """
        Searches for issues within the specified repository using GitHub's search syntax.

        Use this tool to find issues matching specific criteria (keywords, labels, authors, etc.)
        within the context of the repository defined by `owner` and `repo`.

        Args:
            query (str): The search query string, following GitHub's issue search syntax.
                         Example: "is:open label:bug login error"

        Returns:
            list[dict[str, Any]]: A list of dictionaries, where each dictionary represents
                                  the raw data of an issue matching the search query, as
                                  returned by the GitHub API. Consult the GitHub API documentation
                                  for the issue object structure.

        Raises:
            GithubException: If the search API call fails (e.g., rate limiting, invalid query).
            GeminiGithubClientError: For other unexpected errors.
        """
        full_query = f"{query} repo:{self.owner_repo} is:issue"
        logger.info(f"Searching issues with query: {full_query}")
        # PyGithub's search_issues returns a PaginatedList, convert to list of dicts
        issues = self.github.search_issues(query=full_query)
        return [issue.raw_data for issue in issues]
    
    def search_pull_requests(self, query: str) -> list[dict[str, Any]]:
        """
        Searches for pull requests within the specified repository using GitHub's search syntax.

        Use this tool to find pull requests matching specific criteria (keywords, labels, authors, etc.).
        """

        full_query = f"{query} repo:{self.repo_id} is:pr"
        logger.info(f"Searching pull requests with query: {full_query}")
        # PyGithub's search_issues returns a PaginatedList, convert to list of dicts
        pull_requests = self.github.search_issues(query=full_query)
        return [pull_request.raw_data for pull_request in pull_requests]

    def create_pull_request(self, head_branch: str, base_branch: str, title: str, body: str) -> dict[str, Any]:
        """
        Creates a new pull request in the configured repository.

        Use this tool to propose merging changes from one branch (`head_branch`) into
        another (`base_branch`). Note: This client enforces a limit of **one** pull request
        creation per instance to prevent accidental duplicates.

        Args:
            head_branch (str): The name of the branch containing the changes you want to merge.
                               Example: "feature/add-widget"
            base_branch (str): The name of the branch you want to merge the changes into.
                               Often the default branch like "main" or "master".
            title (str): The desired title for the pull request.
            body (str): The description or summary of the changes in the pull request body.

        Returns:
            dict[str, Any]: A dictionary representing the raw data of the newly created
                            pull request, as returned by the GitHub API. Consult the GitHub API
                            documentation for the pull request object structure.

        Raises:
            GeminiGithubClientPRLimitError: If a pull request has already been created by this client instance.
            GeminiGithubClientPRCreateError: If the pull request creation fails via the API (e.g., permissions,
                                             invalid branches, no difference between branches).
            GeminiGithubClientError: For other unexpected errors.
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
