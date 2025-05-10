from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from src.actions.handler import ActionHandler
from src.clients.genai_client import GenAIClient
from src.clients.github_api_client import GitHubAPIClient
from src.config.prompt_manager import PromptManager
from src.main import cli, create_command_handler, get_command_selection_prompt


@pytest.fixture
def runner():
    """Fixture for Click CliRunner."""
    return CliRunner()


@pytest.fixture
def mock_action_handler():
    """Create a mock ActionHandler."""
    handler = Mock(spec=ActionHandler)
    handler.prompt_manager = Mock(spec=PromptManager)
    handler.prompt_manager.get_activation_keywords.return_value = ["gemini"]
    handler.github_api = Mock(spec=GitHubAPIClient)
    handler.ai_model = Mock(spec=GenAIClient)
    return handler


@patch("src.main.ActionHandler")
@patch("src.main.PromptManager")
@patch("src.main.GenAIClient")
@patch("src.main.GitHubAPIClient")
def test_create_command_handler(MockGitHubAPIClient, MockGenAIClient, MockPromptManager, MockActionHandler):
    """Test create_command_handler function."""
    kwargs = {
        "github_token": "test_token",
        "github_owner": "test_owner",
        "github_repo": "test_repo",
        "gemini_api_key": "test_key",
        "model": "test_model",
        "temperature": 0.5,
        "top_p": 0.6,
        "top_k": 30,
    }
    custom_prompts = "test/prompts.yaml"

    handler = create_command_handler(custom_prompts=custom_prompts, **kwargs)

    MockGitHubAPIClient.assert_called_once_with(token="test_token", owner="test_owner", repo="test_repo")
    MockGenAIClient.assert_called_once_with(api_key="test_key", model="test_model", temperature=0.5, top_p=0.6, top_k=30)
    MockPromptManager.assert_called_once_with(custom_prompts_path="test/prompts.yaml")
    MockActionHandler.assert_called_once_with(
        MockGenAIClient.return_value,
        MockGitHubAPIClient.return_value,
        MockPromptManager.return_value,
    )
    assert isinstance(handler, Mock)  # Check if the returned object is the mock handler


def test_get_command_selection_prompt():
    """Test get_command_selection_prompt function."""
    user_message = "Please review this code."
    allowed_commands = ["review_pr", "analyze_code"]
    available_tools = ["get_pull_request_diff", "read_file"]

    prompt = get_command_selection_prompt(user_message, allowed_commands, available_tools)

    expected_prompt = """Given the following user message and available commands, select the most appropriate command to handle the request.

User message: Please review this code.

Available commands:
- review_pr
- analyze_code

Available tools:
- get_pull_request_diff
- read_file

Please respond with ONLY the command name that best matches the user's request. Do not include any other text or explanation."""
    assert prompt == expected_prompt


@patch("src.main.create_command_handler")
def test_pr_command_success(mock_create_command_handler, runner, mock_action_handler):
    """Test pr_command CLI command success."""
    mock_create_command_handler.return_value = mock_action_handler
    mock_action_handler.github_api.get_pr_description.return_value = "gemini review this"
    mock_action_handler.prompt_manager.config = {"available_tools": ["tool1", "tool2"]}
    mock_action_handler.ai_model.generate.return_value = "review_pr"
    mock_action_handler.execute.return_value = "Review completed."

    result = runner.invoke(
        cli,
        [
            "pr-command",
            "--pr-number",
            "123",
            "--allowed-commands",
            "review_pr,analyze_code",
            "--github-token",
            "fake_token",
            "--github-owner",
            "fake_owner",
            "--github-repo",
            "fake_repo",
            "--gemini-api-key",
            "fake_key",
        ],
    )

    assert result.exit_code == 0
    assert "Review completed." in result.output
    mock_create_command_handler.assert_called_once()
    mock_action_handler.github_api.get_pr_description.assert_called_once_with(123)
    mock_action_handler.ai_model.generate.assert_called_once()
    mock_action_handler.execute.assert_called_once_with("review_pr", pr_number=123)


@patch("src.main.create_command_handler")
def test_pr_command_no_activation_keyword(mock_create_command_handler, runner, mock_action_handler):
    """Test pr_command CLI command with no activation keyword."""
    mock_create_command_handler.return_value = mock_action_handler
    mock_action_handler.github_api.get_pr_description.return_value = "just some text"
    mock_action_handler.prompt_manager.get_activation_keywords.return_value = ["gemini"]

    result = runner.invoke(
        cli,
        [
            "pr-command",
            "--pr-number",
            "123",
            "--allowed-commands",
            "review_pr",
            "--github-token",
            "fake_token",
            "--github-owner",
            "fake_owner",
            "--github-repo",
            "fake_repo",
            "--gemini-api-key",
            "fake_key",
        ],
    )

    assert result.exit_code != 0
    assert "No activation keyword found in PR text" in result.output


@patch("src.main.create_command_handler")
def test_pr_command_invalid_selected_command(mock_create_command_handler, runner, mock_action_handler):
    """Test pr_command CLI command with invalid selected command."""
    mock_create_command_handler.return_value = mock_action_handler
    mock_action_handler.github_api.get_pr_description.return_value = "gemini review this"
    mock_action_handler.prompt_manager.config = {"available_tools": ["tool1", "tool2"]}
    mock_action_handler.ai_model.generate.return_value = "invalid_command"
    mock_action_handler.prompt_manager.get_activation_keywords.return_value = ["gemini"]

    result = runner.invoke(
        cli,
        [
            "pr-command",
            "--pr-number",
            "123",
            "--allowed-commands",
            "review_pr",
            "--github-token",
            "fake_token",
            "--github-owner",
            "fake_owner",
            "--github-repo",
            "fake_repo",
            "--gemini-api-key",
            "fake_key",
        ],
    )

    assert result.exit_code != 0
    assert "Selected command 'invalid_command' is not in the allowed commands list" in result.output


@patch("src.main.create_command_handler")
def test_issue_command_success(mock_create_command_handler, runner, mock_action_handler):
    """Test issue_command CLI command success."""
    mock_create_command_handler.return_value = mock_action_handler
    mock_action_handler.github_api.get_issue_description.return_value = "gemini analyze this issue"
    mock_action_handler.prompt_manager.config = {"available_tools": ["tool1", "tool2"]}
    mock_action_handler.ai_model.generate.return_value = "analyze_issue"
    mock_action_handler.execute.return_value = "Issue analyzed."

    result = runner.invoke(
        cli,
        [
            "issue-command",
            "--issue-number",
            "456",
            "--allowed-commands",
            "analyze_issue",
            "--github-token",
            "fake_token",
            "--github-owner",
            "fake_owner",
            "--github-repo",
            "fake_repo",
            "--gemini-api-key",
            "fake_key",
        ],
    )

    assert result.exit_code == 0
    assert "Issue analyzed." in result.output
    mock_create_command_handler.assert_called_once()
    mock_action_handler.github_api.get_issue_description.assert_called_once_with(456)
    mock_action_handler.ai_model.generate.assert_called_once()
    mock_action_handler.execute.assert_called_once_with("analyze_issue", issue_number=456)


@patch("src.main.create_command_handler")
def test_analyze_code_success(mock_create_command_handler, runner, mock_action_handler):
    """Test analyze_code CLI command success."""
    mock_create_command_handler.return_value = mock_action_handler
    mock_action_handler.github_api.get_file_content.return_value = "gemini analyze this code"
    mock_action_handler.prompt_manager.config = {"available_tools": ["tool1", "tool2"]}
    mock_action_handler.ai_model.generate.return_value = "analyze_code"
    mock_action_handler.execute.return_value = "Code analyzed."

    result = runner.invoke(
        cli,
        [
            "analyze-code",
            "--path",
            "src/some_file.py",
            "--allowed-commands",
            "analyze_code",
            "--github-token",
            "fake_token",
            "--github-owner",
            "fake_owner",
            "--github-repo",
            "fake_repo",
            "--gemini-api-key",
            "fake_key",
        ],
    )

    assert result.exit_code == 0
    assert "Code analyzed." in result.output
    mock_create_command_handler.assert_called_once()
    mock_action_handler.github_api.get_file_content.assert_called_once_with("src/some_file.py")
    mock_action_handler.ai_model.generate.assert_called_once()
    mock_action_handler.execute.assert_called_once_with("analyze_code", path="src/some_file.py")
