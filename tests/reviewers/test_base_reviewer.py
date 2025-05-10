from unittest.mock import Mock

import pytest

from src.ai_model.genai_client import GenAIClient
from src.config.prompt_manager import PromptManager
from src.github_api.client import GitHubAPIClient
from src.reviewers.base import BaseReviewer


class MockTool:
    """Mock tool for testing."""

    def __init__(self, name: str):
        self.name = name

    def execute(self, args: dict) -> str:
        return f"Mock result for {self.name}"


@pytest.fixture
def mock_ai_model():
    """Create a mock AI model."""
    return Mock(spec=GenAIClient)


@pytest.fixture
def mock_github_api():
    """Create a mock GitHub API."""
    return Mock(spec=GitHubAPIClient)


@pytest.fixture
def mock_prompt_manager():
    """Create a mock prompt manager."""
    manager = Mock(spec=PromptManager)
    manager.get_prompt.return_value = "Test prompt: {diff}"
    return manager


@pytest.fixture
def mock_tools():
    """Create mock tools."""
    return [MockTool("git_diff"), MockTool("read_file")]


@pytest.fixture
def reviewer(mock_ai_model, mock_github_api, mock_prompt_manager, mock_tools):
    """Create a base reviewer instance."""
    return BaseReviewer(ai_model=mock_ai_model, github_api=mock_github_api, prompt_manager=mock_prompt_manager, tools=mock_tools)


def test_generate_response(reviewer):
    """Test generating a response."""
    # Mock AI model response
    reviewer.ai_model.generate_content.return_value = {"text": "Generated response"}

    result = reviewer._generate_response(prompt_key="test_command", diff="test diff")
    assert result == "Generated response"

    # Verify prompt manager was called
    reviewer.prompt_manager.get_prompt.assert_called_once_with("test_command", diff="test diff")

    # Verify AI model was called with correct arguments
    reviewer.ai_model.generate_content.assert_called_once()
    call_args = reviewer.ai_model.generate_content.call_args[1]
    assert call_args["contents"] == [{"text": "Test prompt: test diff"}]
    assert call_args["tools"] == reviewer.tools
