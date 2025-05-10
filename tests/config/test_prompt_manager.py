import pytest

from src.config.prompt_manager import PromptManager


@pytest.fixture
def custom_prompts_yaml(tmp_path):
    """Create a temporary custom prompts YAML file."""
    yaml_content = """
    activation_keywords:
      - gemini

    commands:
      review_pr:
        description: "review this pr"
        prompt: "Custom review prompt: {diff}"
        tools:
          - git_diff
          - read_file

    slugs:
      custom_review:
        command: "do a custom review"
        prompt: "Custom slug prompt: {diff}"
        tools:
          - git_diff
          - read_file
          - write_file
    """
    yaml_file = tmp_path / "custom_prompts.yaml"
    yaml_file.write_text(yaml_content)
    return str(yaml_file)


@pytest.fixture
def prompt_manager(custom_prompts_yaml):
    """Create a prompt manager with custom prompts."""
    return PromptManager(custom_prompts_yaml)


def test_get_activation_keywords(prompt_manager):
    """Test getting activation keywords."""
    keywords = prompt_manager.get_activation_keywords()
    assert "custom_bot" in keywords
    assert "ai_assistant" in keywords
    assert "gemini" not in keywords  # Should be overridden by custom config


def test_parse_command_with_custom_keyword(prompt_manager):
    """Test parsing commands with custom activation keywords."""
    # Test built-in command with custom keyword
    result = prompt_manager.parse_command("custom_bot review this pr")
    assert result is not None
    command_type, config = result
    assert command_type == "review_pr"
    assert config["description"] == "review this pr"

    # Test custom slug with custom keyword
    result = prompt_manager.parse_command("ai_assistant do a custom review")
    assert result is not None
    command_type, config = result
    assert command_type == "custom_review"
    assert config["command"] == "do a custom review"


def test_parse_command_case_insensitive(prompt_manager):
    """Test that command parsing is case insensitive."""
    # Test activation keyword
    result = prompt_manager.parse_command("CUSTOM_BOT review this pr")
    assert result is not None

    # Test command text
    result = prompt_manager.parse_command("custom_bot REVIEW THIS PR")
    assert result is not None


def test_parse_command_no_match(prompt_manager):
    """Test parsing commands that don't match any patterns."""
    # Wrong activation keyword
    result = prompt_manager.parse_command("unknown_bot review this pr")
    assert result is None

    # Wrong command text
    result = prompt_manager.parse_command("custom_bot unknown command")
    assert result is None


def test_get_prompt(prompt_manager):
    """Test getting and formatting prompts."""
    # Test built-in command prompt
    prompt = prompt_manager.get_prompt("review_pr", diff="test diff")
    assert prompt == "Custom review prompt: test diff"

    # Test custom slug prompt
    prompt = prompt_manager.get_prompt("custom_review", diff="test diff")
    assert prompt == "Custom slug prompt: test diff"


def test_get_tools(prompt_manager):
    """Test getting required tools for commands."""
    # Test built-in command tools
    tools = prompt_manager.get_tools("review_pr")
    assert set(tools) == {"git_diff", "read_file"}

    # Test custom slug tools
    tools = prompt_manager.get_tools("custom_review")
    assert set(tools) == {"git_diff", "read_file", "write_file"}


def test_missing_prompt(prompt_manager):
    """Test handling of missing prompts."""
    with pytest.raises(KeyError):
        prompt_manager.get_prompt("nonexistent_command")

    with pytest.raises(KeyError):
        prompt_manager.get_tools("nonexistent_command")


def test_default_prompt_manager():
    """Test prompt manager with default configuration."""
    manager = PromptManager()

    # Should have default activation keyword
    assert "gemini" in manager.get_activation_keywords()

    # Should have default commands
    result = manager.parse_command("gemini review a pull request")
    assert result is not None
    command_type, config = result
    assert command_type == "review_pr"

    # Should have default tools
    tools = manager.get_tools("review_pr")
    assert "git_diff" in tools
    assert "read_file" in tools
