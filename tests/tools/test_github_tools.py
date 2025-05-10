from unittest.mock import Mock

import pytest

from src.clients.github_api_client import GitHubAPIClient
from src.tools.github_tools import create_issue_comment, create_pr_review, get_file_content, get_issue_body, get_pull_request_diff


@pytest.fixture
def mock_github_api_client():
    """Create a mock GitHubAPIClient."""
    return Mock(spec=GitHubAPIClient)


def test_get_pull_request_diff(mock_github_api_client):
    """Test get_pull_request_diff tool function."""
    mock_github_api_client.get_pull_request_diff.return_value = "mock diff"
    owner = "test_owner"
    repo = "test_repo"
    pr_number = 123

    diff = get_pull_request_diff(mock_github_api_client, owner, repo, pr_number)

    mock_github_api_client.get_pull_request_diff.assert_called_once_with(owner, repo, pr_number)
    assert diff == "mock diff"


def test_get_issue_body(mock_github_api_client):
    """Test get_issue_body tool function."""
    mock_github_api_client.get_issue_body.return_value = "mock issue body"
    owner = "test_owner"
    repo = "test_repo"
    issue_number = 456

    body = get_issue_body(mock_github_api_client, owner, repo, issue_number)

    mock_github_api_client.get_issue_body.assert_called_once_with(owner, repo, issue_number)
    assert body == "mock issue body"


def test_create_pr_review(mock_github_api_client):
    """Test create_pr_review tool function."""
    owner = "test_owner"
    repo = "test_repo"
    pr_number = 123
    body = "mock review body"
    event = "COMMENT"

    create_pr_review(mock_github_api_client, owner, repo, pr_number, body, event)

    mock_github_api_client.create_pr_review.assert_called_once_with(owner, repo, pr_number, body, event)


def test_create_issue_comment(mock_github_api_client):
    """Test create_issue_comment tool function."""
    owner = "test_owner"
    repo = "test_repo"
    issue_number = 456
    body = "mock comment body"

    create_issue_comment(mock_github_api_client, owner, repo, issue_number, body)

    mock_github_api_client.create_issue_comment.assert_called_once_with(owner, repo, issue_number, body)


def test_get_file_content(mock_github_api_client):
    """Test get_file_content tool function."""
    mock_github_api_client.get_file_content.return_value = "mock file content"
    owner = "test_owner"
    repo = "test_repo"
    path = "test/path/to/file.txt"

    content = get_file_content(mock_github_api_client, owner, repo, path)

    mock_github_api_client.get_file_content.assert_called_once_with(owner, repo, path)
    assert content == "mock file content"
