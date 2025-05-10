from unittest.mock import Mock, patch

import pytest
from github import Github
from github.ContentFile import ContentFile
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Repository import Repository

from src.clients.github_api_client import GitHubAPIClient


@pytest.fixture
def mock_github_instance():
    """Create a mock PyGithub Github instance."""
    return Mock(spec=Github)


@pytest.fixture
def github_api_client(mock_github_instance):
    """Create a GitHubAPIClient instance with a mocked Github instance."""
    with patch("src.clients.github_api_client.Github", return_value=mock_github_instance):
        return GitHubAPIClient(token="fake_token")


@pytest.fixture
def mock_repo(mock_github_instance):
    """Create a mock Repository instance."""
    repo = Mock(spec=Repository)
    mock_github_instance.get_repo.return_value = repo
    return repo


@pytest.fixture
def mock_pr(mock_repo):
    """Create a mock PullRequest instance."""
    pr = Mock(spec=PullRequest)
    mock_repo.get_pull.return_value = pr
    return pr


@pytest.fixture
def mock_issue(mock_repo):
    """Create a mock Issue instance."""
    issue = Mock(spec=Issue)
    mock_repo.get_issue.return_value = issue
    return issue


@pytest.fixture
def mock_content_file(mock_repo):
    """Create a mock ContentFile instance."""
    content_file = Mock(spec=ContentFile)
    mock_repo.get_contents.return_value = content_file
    return content_file


def test_get_pull_request_diff(github_api_client, mock_repo, mock_pr):
    """Test get_pull_request_diff method."""
    mock_file1 = Mock()
    mock_file1.patch = "diff of file1"
    mock_file2 = Mock()
    mock_file2.patch = "diff of file2"
    mock_pr.get_files.return_value = [mock_file1, mock_file2]

    owner = "test_owner"
    repo = "test_repo"
    pull_number = 123

    diff = github_api_client.get_pull_request_diff(owner, repo, pull_number)

    mock_github_instance = github_api_client.github
    mock_github_instance.get_repo.assert_called_once_with(f"{owner}/{repo}")
    mock_repo.get_pull.assert_called_once_with(pull_number)
    mock_pr.get_files.assert_called_once()
    assert diff == "diff of file1\ndiff of file2"


def test_create_pr_review(github_api_client, mock_repo, mock_pr):
    """Test create_pr_review method."""
    mock_review = Mock()
    mock_review.raw_data = {"id": 123, "body": "test review"}
    mock_pr.create_review.return_value = mock_review

    owner = "test_owner"
    repo = "test_repo"
    pull_number = 123
    body = "test review body"
    event = "COMMENT"

    review_data = github_api_client.create_pr_review(owner, repo, pull_number, body, event)

    mock_github_instance = github_api_client.github
    mock_github_instance.get_repo.assert_called_once_with(f"{owner}/{repo}")
    mock_repo.get_pull.assert_called_once_with(pull_number)
    mock_pr.create_review.assert_called_once_with(body=body, event=event)
    assert review_data == {"id": 123, "body": "test review"}


def test_get_issue_body(github_api_client, mock_repo, mock_issue):
    """Test get_issue_body method."""
    mock_issue.body = "test issue body"

    owner = "test_owner"
    repo = "test_repo"
    issue_number = 456

    issue_body = github_api_client.get_issue_body(owner, repo, issue_number)

    mock_github_instance = github_api_client.github
    mock_github_instance.get_repo.assert_called_once_with(f"{owner}/{repo}")
    mock_repo.get_issue.assert_called_once_with(issue_number)
    assert issue_body == "test issue body"


def test_create_issue_comment(github_api_client, mock_repo, mock_issue):
    """Test create_issue_comment method."""
    mock_comment = Mock()
    mock_comment.raw_data = {"id": 456, "body": "test comment"}
    mock_issue.create_comment.return_value = mock_comment

    owner = "test_owner"
    repo = "test_repo"
    issue_number = 456
    body = "test comment body"

    comment_data = github_api_client.create_issue_comment(owner, repo, issue_number, body)

    mock_github_instance = github_api_client.github
    mock_github_instance.get_repo.assert_called_once_with(f"{owner}/{repo}")
    mock_repo.get_issue.assert_called_once_with(issue_number)
    mock_issue.create_comment.assert_called_once_with(body)
    assert comment_data == {"id": 456, "body": "test comment"}


def test_get_file_content(github_api_client, mock_repo, mock_content_file):
    """Test get_file_content method."""
    mock_content_file.decoded_content.decode.return_value = "test file content"

    owner = "test_owner"
    repo = "test_repo"
    path = "test/path/to/file.txt"
    ref = "main"

    file_content = github_api_client.get_file_content(owner, repo, path, ref)

    mock_github_instance = github_api_client.github
    mock_github_instance.get_repo.assert_called_once_with(f"{owner}/{repo}")
    mock_repo.get_contents.assert_called_once_with(path, ref=ref)
    mock_content_file.decoded_content.decode.assert_called_once_with("utf-8")
    assert file_content == "test file content"
