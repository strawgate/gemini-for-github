from unittest.mock import Mock, patch

import pytest

from src.actions.handler import ActionHandler
from src.clients.genai_client import GenAIClient
from src.clients.github_api_client import GitHubAPIClient
from src.config.prompt_manager import PromptManager
from src.main import cli


# Mock the concrete client classes
@pytest.fixture
def mock_github_api_client():
    """Mock GitHubAPIClient."""
    return Mock(spec=GitHubAPIClient)


@pytest.fixture
def mock_genai_client():
    """Mock GenAIClient."""
    return Mock(spec=GenAIClient)


@pytest.fixture
def mock_prompt_manager():
    """Mock PromptManager."""
    manager = Mock(spec=PromptManager)
    manager.get_activation_keywords.return_value = ["gemini"]
    # Configure mock prompt_manager to return a simple prompt and tools for a command
    manager.get_prompt.return_value = "Analyze this: {content}"
    manager.get_tools.return_value = ["read_file"]
    manager.config = {"available_tools": ["read_file"]}  # Needed by main.py
    return manager


# Mock the ActionHandler's dependencies when creating it in the CLI
@patch("src.main.GitHubAPIClient")
@patch("src.main.GenAIClient")
@patch("src.main.PromptManager")
@patch("src.main.ActionHandler")
def test_cli_pr_command_integration(
    MockActionHandler,
    MockPromptManager,
    MockGenAIClient,
    MockGitHubAPIClient,
    runner,
    mock_action_handler,  # Use the fixture to get a configured mock handler
):
    """Test the integration of the CLI pr-command with ActionHandler and mocked tools."""
    # Configure the mocks returned by create_command_handler
    MockGitHubAPIClient.return_value = mock_action_handler.github_api
    MockGenAIClient.return_value = mock_action_handler.ai_model
    MockPromptManager.return_value = mock_action_handler.prompt_manager
    MockActionHandler.return_value = mock_action_handler

    # Configure the mock ActionHandler's behavior
    mock_action_handler.github_api.get_pr_description.return_value = "gemini analyze this code"
    mock_action_handler.ai_model.generate.return_value = "analyze_code"  # Simulate LLM selecting a command
    mock_action_handler.execute.return_value = "Analysis complete."  # Simulate ActionHandler execution result

    result = runner.invoke(
        cli,
        [
            "pr-command",
            "--pr-number",
            "123",
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
    assert "Analysis complete." in result.output

    # Verify that create_command_handler was called with correct arguments
    MockGitHubAPIClient.assert_called_once_with(token="fake_token", owner="fake_owner", repo="fake_repo")
    MockGenAIClient.assert_called_once_with(
        api_key="fake_key",
        model="gemini-1.5-flash",
        temperature=0.7,
        top_p=0.8,
        top_k=40,  # Default values from main.py
    )
    MockPromptManager.assert_called_once_with(custom_prompts_path=None)
    MockActionHandler.assert_called_once_with(
        mock_action_handler.ai_model,
        mock_action_handler.github_api,
        mock_action_handler.prompt_manager,
    )

    # Verify the flow through the ActionHandler
    mock_action_handler.github_api.get_pr_description.assert_called_once_with(123)
    mock_action_handler.prompt_manager.get_activation_keywords.assert_called_once()
    mock_action_handler.ai_model.generate.assert_called_once()  # Called to select command
    mock_action_handler.execute.assert_called_once_with("analyze_code", pr_number=123)


# Add similar integration tests for issue_command and analyze_code CLI commands
# These tests would follow a similar pattern, mocking the dependencies and verifying the call flow.


# Example of testing the ActionHandler's execute method with tool calling
@patch("src.actions.handler.GenAIClient")
@patch("src.actions.handler.GitHubAPIClient")
@patch("src.actions.handler.PromptManager")
@patch("src.actions.handler.get_file_content")  # Patch the specific tool function
def test_action_handler_execute_with_tool_call(
    mock_get_file_content,
    MockPromptManager,
    MockGitHubAPIClient,
    MockGenAIClient,
):
    """Test ActionHandler.execute method with a simulated tool call."""
    # Configure mocks
    mock_genai_client_instance = Mock(spec=GenAIClient)
    mock_github_api_client_instance = Mock(spec=GitHubAPIClient)
    mock_prompt_manager_instance = Mock(spec=PromptManager)

    MockGenAIClient.return_value = mock_genai_client_instance
    MockGitHubAPIClient.return_value = mock_github_api_client_instance
    MockPromptManager.return_value = mock_prompt_manager_instance

    # Configure prompt manager to return a prompt that requires a tool
    mock_prompt_manager_instance.get_prompt.return_value = "Get content of file: {path}"
    mock_prompt_manager_instance.get_tools.return_value = ["get_file_content"]
    mock_prompt_manager_instance.config = {"available_tools": ["get_file_content"]}

    # Configure the AI model to return a tool call response first, then a text response
    mock_genai_client_instance.generate_content.side_effect = [
        {  # First response: tool call
            "tool_calls": [
                {"function": {"name": "get_file_content", "args": {"owner": "test_owner", "repo": "test_repo", "path": "test.txt"}}},
            ],
        },
        {  # Second response: text after tool output
            "text": "File content is: mock file content",
        },
    ]

    # Configure the tool function's return value
    mock_get_file_content.return_value = "mock file content"

    # Create ActionHandler instance
    handler = ActionHandler(
        ai_model=mock_genai_client_instance,
        github_api=mock_github_api_client_instance,
        prompt_manager=mock_prompt_manager_instance,
    )

    # Execute the action
    result = handler.execute("analyze_file", path="test.txt")

    # Assertions
    mock_prompt_manager_instance.get_prompt.assert_called_once_with("analyze_file", path="test.txt")
    mock_genai_client_instance.generate_content.call_count == 2  # Called twice for tool loop

    # Verify the first call to generate_content
    first_call_args = mock_genai_client_instance.generate_content.call_args_list[0][1]
    assert first_call_args["contents"] == [{"role": "user", "parts": [{"text": "Get content of file: test.txt"}]}]
    assert "tools" in first_call_args

    # Verify the tool function was called with correct arguments
    mock_get_file_content.assert_called_once_with(
        owner="test_owner",
        repo="test_repo",
        path="test.txt",
    )  # Note: owner and repo are hardcoded in the mock tool call

    # Verify the second call to generate_content includes tool output
    second_call_args = mock_genai_client_instance.generate_content.call_args_list[1][1]
    assert len(second_call_args["contents"]) == 3  # User, Model (tool call), Tool (output)
    assert second_call_args["contents"][2]["role"] == "tool"
    assert second_call_args["contents"][2]["parts"][0]["stdout"] == "mock file content"

    assert result == "File content is: mock file content"
