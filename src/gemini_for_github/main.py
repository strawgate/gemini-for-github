import logging

import click

from .actions.handler import ActionHandler
from .clients.genai_client import GenAIClient
from .clients.github_api_client import GitHubAPIClient
from .config.prompt_manager import PromptManager
from .mcp_integration.mcp_client_manager import MCPClientManager  # Import MCPClientManager

logger = logging.getLogger(__name__)


def get_common_options():
    """Common options for all commands."""
    return [
        click.option("--github-token", envvar="GITHUB_TOKEN", required=True, help="GitHub API token"),
        click.option("--github-owner", envvar="GITHUB_OWNER", required=True, help="GitHub repository owner"),
        click.option("--github-repo", envvar="GITHUB_REPO", required=True, help="GitHub repository name"),
        click.option("--gemini-api-key", envvar="GEMINI_API_KEY", required=True, help="Gemini API key"),
        click.option("--model", envvar="GEMINI_MODEL", default="gemini-1.5-flash", help="Gemini model to use"),
        click.option("--temperature", envvar="GEMINI_TEMPERATURE", type=float, default=0.7, help="Model temperature"),
        click.option("--top-p", envvar="GEMINI_TOP_P", type=float, default=0.8, help="Model top_p"),
        click.option("--top-k", envvar="GEMINI_TOP_K", type=int, default=40, help="Model top_k"),
        click.option("--activation-keywords", type=str, help="Comma-separated list of activation keywords (e.g., gemini,bill2.0)"),
    ]


def create_command_handler(
    custom_prompts: str | None = None,
    mcp_config: str = "src/gemini_for_github/mcp_integration/mcp_servers.yaml",
    activation_keywords: str | None = None,
    **kwargs,
) -> ActionHandler:
    """Create a command handler with the given configuration."""
    github_api = GitHubAPIClient(token=kwargs["github_token"], owner=kwargs["github_owner"], repo=kwargs["github_repo"])
    ai_model = GenAIClient(
        api_key=kwargs["gemini_api_key"],
        model=kwargs["model"],
        temperature=kwargs["temperature"],
        top_p=kwargs["top_p"],
        top_k=kwargs["top_k"],
    )

    activation_keywords_list = [kw.strip() for kw in activation_keywords.split(",")] if activation_keywords else None
    prompt_manager = PromptManager(custom_prompts_path=custom_prompts, cli_activation_keywords=activation_keywords_list)

    # Instantiate and connect MCPClientManager
    mcp_client_manager = MCPClientManager(config_path=mcp_config)  # Pass config path
    mcp_client_manager.load_config()
    mcp_client_manager.connect_to_servers()  # This will discover tools

    return ActionHandler(ai_model, github_api, prompt_manager, mcp_client_manager)  # Pass the manager


def get_command_selection_prompt(user_message: str, allowed_commands: list[str], available_tools: list[str]) -> str:
    """Generate a prompt for the LLM to select the appropriate command with a confidence score."""
    return f"""Given the following user message and available commands, select the single most appropriate command to handle the request.

User message: {user_message}

Available commands:
{chr(10).join(f"- {cmd}" for cmd in allowed_commands)}

Available tools:
{chr(10).join(f"- {tool}" for tool in available_tools)}

Please respond with a JSON object containing the selected command and a confidence score (0.0 to 1.0). The JSON object should have the following structure:
{{
  "command": "selected_command_name",
  "confidence": 0.95
}}
Ensure your response contains ONLY the JSON object and nothing else.
"""


@click.group()
def cli():
    """Gemini for GitHub CLI."""


@cli.command()
@click.option("--pr-number", required=True, type=int, help="Pull request number")
@click.option("--allowed-commands", required=True, help="Comma-separated list of allowed commands")
@click.option("--allowed-tools", help="Comma-separated list of allowed tools (defaults to all available tools)")
@click.option("--custom-prompts", type=str, help="Path to custom prompts YAML file")
@click.option(
    "--mcp-config",
    type=str,
    default="src/gemini_for_github/mcp_integration/mcp_servers.yaml",
    help="Path to MCP servers configuration YAML file",
)
@click.option("--activation-keywords", type=str, help="Comma-separated list of activation keywords (overrides YAML)")  # Added
def pr_command(
    pr_number: int,
    allowed_commands: str,
    allowed_tools: str | None,
    custom_prompts: str | None,
    mcp_config: str,
    activation_keywords: str | None,
    **kwargs,
):
    """Execute a command on a pull request."""
    logger.info(f"Starting pr_command for PR #{pr_number}")
    try:
        handler = create_command_handler(
            custom_prompts=custom_prompts,
            mcp_config=mcp_config,
            activation_keywords=activation_keywords,  # Pass to handler
            **kwargs,
        )
        prompt_manager = handler.prompt_manager

        # Get PR description
        try:
            pr_text = handler.github_api.get_pr_description(pr_number)
            logger.info(f"Successfully fetched description for PR #{pr_number}")
        except Exception as e:
            logger.error(f"Failed to fetch PR description for #{pr_number}: {e}", exc_info=True)
            msg = f"Failed to fetch PR description for #{pr_number}: {e}"
            raise click.ClickException(msg)

        # Parse activation keyword and get user message
        activation_keywords = prompt_manager.get_activation_keywords()
        user_message = None
        for keyword in activation_keywords:
            if pr_text.lower().startswith(keyword.lower()):
                user_message = pr_text[len(keyword) :].strip()
                logger.info(f"Activation keyword found. User message: {user_message[:100]}...")  # Log first 100 chars
                break

        if not user_message:
            logger.warning(f"No activation keyword found in PR text for #{pr_number}")
            msg = "No activation keyword found in PR text"
            raise click.ClickException(msg)

        # Get all available tool names from PromptManager (which now uses MCPClientManager)
        all_available_tool_names = prompt_manager.get_all_available_tool_names(handler.mcp_client_manager)
        logger.debug(f"All available tools: {all_available_tool_names}")

        # Filter available tools based on --allowed-tools CLI option
        available_tools_for_prompt = all_available_tool_names
        if allowed_tools:
            allowed_tools_list = [tool.strip() for tool in allowed_tools.split(",")]
            available_tools_for_prompt = [tool for tool in all_available_tool_names if tool in allowed_tools_list]
            logger.info(f"Filtered available tools based on --allowed-tools: {available_tools_for_prompt}")

        # Get allowed commands
        allowed_commands_list = [cmd.strip() for cmd in allowed_commands.split(",")]
        logger.debug(f"Allowed commands: {allowed_commands_list}")

        # Use LLM to select the appropriate command with automatic function calling
        selection_prompt = get_command_selection_prompt(
            user_message,
            allowed_commands_list,
            available_tools_for_prompt,
        )  # Use filtered list
        logger.debug(f"Command selection prompt: {selection_prompt}")

        try:
            # The SDK handles the function call and returns the final text
            # The ActionHandler now handles manual tool execution
            logger.info("Requesting command selection from LLM...")
            selection_response_text = handler.execute(  # Call handler.execute directly
                action="select_command",  # Assuming a prompt key for command selection exists
                user_message=user_message,
                allowed_commands=allowed_commands_list,
                available_tools=available_tools_for_prompt,  # Pass filtered list
            ).strip()
            logger.info(f"LLM command selection response: {selection_response_text}")

            import json

            selection_data = json.loads(selection_response_text)
            selected_command = selection_data.get("command")
            confidence = selection_data.get("confidence")

            if confidence is not None and confidence < 0.8:  # Example threshold for low confidence
                logger.warning(f"Low confidence score ({confidence}) for selected command: '{selected_command}'")
                # TODO: Consider adding logic here for low confidence, e.g., asking for user confirmation or a fallback command.
                # For now, we will proceed but log the warning.

            logger.info(f"AI selected command: '{selected_command}' with confidence: {confidence}")

        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI command selection response as JSON: {selection_response_text}", exc_info=True)
            msg = f"Failed to parse AI command selection response as JSON: {selection_response_text}"
            raise click.ClickException(msg)
        except Exception as e:
            logger.error(f"Error during AI command selection: {e}", exc_info=True)
            msg = f"Error during AI command selection: {e}"
            raise click.ClickException(msg)

        if selected_command not in allowed_commands_list:
            logger.error(f"Selected command '{selected_command}' is not in the allowed commands list: {allowed_commands_list}")
            msg = f"Selected command '{selected_command}' is not in the allowed commands list"
            raise click.ClickException(msg)

        # Execute the selected command
        logger.info(f"Executing selected command: '{selected_command}' for PR #{pr_number}")
        try:
            response = handler.execute(selected_command, pr_number=pr_number)
            logger.info(f"Command '{selected_command}' completed successfully for PR #{pr_number}")
            print(response)
        except Exception as e:
            logger.error(f"Error executing command '{selected_command}' for PR #{pr_number}: {e}", exc_info=True)
            msg = f"Error executing command '{selected_command}' for PR #{pr_number}: {e}"
            raise click.ClickException(msg)

    except click.ClickException:
        # Re-raise ClickExceptions as they are intended to be shown to the user
        raise
    except Exception as e:
        # Catch other exceptions, log them, and raise a generic ClickException
        logger.error(f"An unexpected error occurred while executing command for PR #{pr_number}: {e}", exc_info=True)
        msg = f"An unexpected error occurred: {e}"
        raise click.ClickException(msg)


@cli.command()
@click.option("--issue-number", required=True, type=int, help="Issue number")
@click.option("--allowed-commands", required=True, help="Comma-separated list of allowed commands")
@click.option("--allowed-tools", help="Comma-separated list of allowed tools (defaults to all available tools)")
@click.option("--custom-prompts", type=str, help="Path to custom prompts YAML file")
@click.option(
    "--mcp-config",
    type=str,
    default="src/gemini_for_github/mcp_integration/mcp_servers.yaml",
    help="Path to MCP servers configuration YAML file",
)
@click.option("--activation-keywords", type=str, help="Comma-separated list of activation keywords (overrides YAML)")  # Added
def issue_command(
    issue_number: int,
    allowed_commands: str,
    allowed_tools: str | None,
    custom_prompts: str | None,
    mcp_config: str,
    activation_keywords: str | None,
    **kwargs,
):
    """Execute a command on an issue."""
    logger.info(f"Starting issue_command for issue #{issue_number}")
    try:
        handler = create_command_handler(
            custom_prompts=custom_prompts,
            mcp_config=mcp_config,
            activation_keywords=activation_keywords,  # Pass to handler
            **kwargs,
        )
        prompt_manager = handler.prompt_manager

        # Get issue description
        try:
            issue_text = handler.github_api.get_issue_description(issue_number)
            logger.info(f"Successfully fetched description for issue #{issue_number}")
        except Exception as e:
            logger.error(f"Failed to fetch issue description for #{issue_number}: {e}", exc_info=True)
            msg = f"Failed to fetch issue description for #{issue_number}: {e}"
            raise click.ClickException(msg)

        # Parse activation keyword and get user message
        activation_keywords = prompt_manager.get_activation_keywords()
        user_message = None
        for keyword in activation_keywords:
            if issue_text.lower().startswith(keyword.lower()):
                user_message = issue_text[len(keyword) :].strip()
                logger.info(f"Activation keyword found. User message: {user_message[:100]}...")  # Log first 100 chars
                break

        if not user_message:
            logger.warning(f"No activation keyword found in issue text for #{issue_number}")
            msg = "No activation keyword found in issue text"
            raise click.ClickException(msg)

        # Get all available tool names from PromptManager
        all_available_tool_names = prompt_manager.get_all_available_tool_names(handler.mcp_client_manager)
        logger.debug(f"All available tools: {all_available_tool_names}")

        # Filter available tools based on --allowed-tools CLI option
        available_tools_for_prompt = all_available_tool_names
        if allowed_tools:
            allowed_tools_list = [tool.strip() for tool in allowed_tools.split(",")]
            available_tools_for_prompt = [tool for tool in all_available_tool_names if tool in allowed_tools_list]
            logger.info(f"Filtered available tools based on --allowed-tools: {available_tools_for_prompt}")

        # Get allowed commands
        allowed_commands_list = [cmd.strip() for cmd in allowed_commands.split(",")]
        logger.debug(f"Allowed commands: {allowed_commands_list}")

        # Use LLM to select the appropriate command with automatic function calling
        selection_prompt = get_command_selection_prompt(
            user_message,
            allowed_commands_list,
            available_tools_for_prompt,
        )  # Use filtered list
        logger.debug(f"Command selection prompt: {selection_prompt}")

        try:
            # The ActionHandler now handles manual tool execution
            logger.info("Requesting command selection from LLM...")
            selection_response_text = handler.execute(  # Call handler.execute directly
                action="select_command",  # Assuming a prompt key for command selection exists
                user_message=user_message,
                allowed_commands=allowed_commands_list,
                available_tools=available_tools_for_prompt,  # Pass filtered list
            ).strip()
            logger.info(f"LLM command selection response: {selection_response_text}")

            import json

            selection_data = json.loads(selection_response_text)
            selected_command = selection_data.get("command")
            confidence = selection_data.get("confidence")

            if confidence is not None and confidence < 0.8:  # Example threshold for low confidence
                logger.warning(f"Low confidence score ({confidence}) for selected command: '{selected_command}'")
                # TODO: Consider adding logic here for low confidence, e.g., asking for user confirmation or a fallback command.
                # For now, we will proceed but log the warning.

            logger.info(f"AI selected command: '{selected_command}' with confidence: {confidence}")

            if selected_command not in allowed_commands_list:
                logger.error(f"Selected command '{selected_command}' is not in the allowed commands list: {allowed_commands_list}")
                msg = f"Selected command '{selected_command}' is not in the allowed commands list"
                raise click.ClickException(msg)

            # Execute the selected command
            logger.info(f"Executing selected command: '{selected_command}' for issue #{issue_number}")
            try:
                response = handler.execute(selected_command, issue_number=issue_number)
                logger.info(f"Command '{selected_command}' completed successfully for issue #{issue_number}")
                print(response)
            except Exception as e:
                logger.error(f"Error executing command '{selected_command}' for issue #{issue_number}: {e}", exc_info=True)
                msg = f"Error executing command '{selected_command}' for issue #{issue_number}: {e}"
                raise click.ClickException(msg)

        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI command selection response as JSON: {selection_response_text}", exc_info=True)
            msg = f"Failed to parse AI command selection response as JSON: {selection_response_text}"
            raise click.ClickException(msg)
        except Exception as e:
            logger.error(f"Error during AI command selection or execution: {e}", exc_info=True)
            msg = f"Error during AI command selection or execution: {e}"
            raise click.ClickException(msg)

    except click.ClickException:
        # Re-raise ClickExceptions as they are intended to be shown to the user
        raise
    except Exception as e:
        # Catch other exceptions, log them, and raise a generic ClickException
        logger.error(f"An unexpected error occurred while executing command for issue #{issue_number}: {e}", exc_info=True)
        msg = f"An unexpected error occurred: {e}"
        raise click.ClickException(msg)


@cli.command()
@click.option("--path", required=True, type=str, help="Path to analyze")
@click.option("--allowed-commands", required=True, help="Comma-separated list of allowed commands")
@click.option("--allowed-tools", help="Comma-separated list of allowed tools (defaults to all available tools)")
@click.option("--custom-prompts", type=str, help="Path to custom prompts YAML file")
@click.option(
    "--mcp-config",
    type=str,
    default="src/gemini_for_github/mcp_integration/mcp_servers.yaml",
    help="Path to MCP servers configuration YAML file",
)
@click.option("--activation-keywords", type=str, help="Comma-separated list of activation keywords (overrides YAML)")  # Added
def analyze_code(
    path: str,
    allowed_commands: str,
    allowed_tools: str | None,
    custom_prompts: str | None,
    mcp_config: str,
    activation_keywords: str | None,
    **kwargs,
):
    """Analyze code in a directory."""
    logger.info(f"Starting analyze_code for path: {path}")
    try:
        handler = create_command_handler(
            custom_prompts=custom_prompts,
            mcp_config=mcp_config,
            activation_keywords=activation_keywords,  # Pass to handler
            **kwargs,
        )
        prompt_manager = handler.prompt_manager

        # Get code content
        try:
            code_text = handler.github_api.get_file_content(path)
            logger.info(f"Successfully fetched content for path: {path}")
        except Exception as e:
            logger.error(f"Failed to fetch file content for {path}: {e}", exc_info=True)
            msg = f"Failed to fetch file content for {path}: {e}"
            raise click.ClickException(msg)

        # Parse activation keyword and get user message
        activation_keywords = prompt_manager.get_activation_keywords()
        user_message = None
        for keyword in activation_keywords:
            if code_text.lower().startswith(keyword.lower()):
                user_message = code_text[len(keyword) :].strip()
                logger.info(f"Activation keyword found. User message: {user_message[:100]}...")  # Log first 100 chars
                break

        if not user_message:
            logger.warning(f"No activation keyword found in code text for {path}")
            msg = "No activation keyword found in code text"
            raise click.ClickException(msg)

        # Get all available tool names from PromptManager
        all_available_tool_names = prompt_manager.get_all_available_tool_names(handler.mcp_client_manager)
        logger.debug(f"All available tools: {all_available_tool_names}")

        # Filter available tools based on --allowed-tools CLI option
        available_tools_for_prompt = all_available_tool_names
        if allowed_tools:
            allowed_tools_list = [tool.strip() for tool in allowed_tools.split(",")]
            available_tools_for_prompt = [tool for tool in all_available_tool_names if tool in allowed_tools_list]
            logger.info(f"Filtered available tools based on --allowed-tools: {available_tools_for_prompt}")

        # Get allowed commands
        allowed_commands_list = [cmd.strip() for cmd in allowed_commands.split(",")]
        logger.debug(f"Allowed commands: {allowed_commands_list}")

        # Use LLM to select the appropriate command with automatic function calling
        selection_prompt = get_command_selection_prompt(
            user_message,
            allowed_commands_list,
            available_tools_for_prompt,
        )  # Use filtered list
        logger.debug(f"Command selection prompt: {selection_prompt}")

        try:
            # The ActionHandler now handles manual tool execution
            logger.info("Requesting command selection from LLM...")
            selection_response_text = handler.execute(  # Call handler.execute directly
                action="select_command",  # Assuming a prompt key for command selection exists
                user_message=user_message,
                allowed_commands=allowed_commands_list,
                available_tools=available_tools_for_prompt,  # Pass filtered list
            ).strip()
            logger.info(f"LLM command selection response: {selection_response_text}")

            import json

            selection_data = json.loads(selection_response_text)
            selected_command = selection_data.get("command")
            confidence = selection_data.get("confidence")

            if confidence is not None and confidence < 0.8:  # Example threshold for low confidence
                logger.warning(f"Low confidence score ({confidence}) for selected command: '{selected_command}'")
                # TODO: Consider adding logic here for low confidence, e.g., asking for user confirmation or a fallback command.
                # For now, we will proceed but log the warning.

            logger.info(f"AI selected command: '{selected_command}' with confidence: {confidence}")

            if selected_command not in allowed_commands_list:
                logger.error(f"Selected command '{selected_command}' is not in the allowed commands list: {allowed_commands_list}")
                msg = f"Selected command '{selected_command}' is not in the allowed commands list"
                raise click.ClickException(msg)

            # Execute the selected command
            logger.info(f"Executing selected command: '{selected_command}' for path: {path}")
            try:
                response = handler.execute(selected_command, path=path)
                logger.info(f"Command '{selected_command}' completed successfully for path: {path}")
                print(response)
            except Exception as e:
                logger.error(f"Error executing command '{selected_command}' for path: {path}: {e}", exc_info=True)
                msg = f"Error executing command '{selected_command}' for path: {path}: {e}"
                raise click.ClickException(msg)

        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI command selection response as JSON: {selection_response_text}", exc_info=True)
            msg = f"Failed to parse AI command selection response as JSON: {selection_response_text}"
            raise click.ClickException(msg)
        except Exception as e:
            logger.error(f"Error during AI command selection or execution: {e}", exc_info=True)
            msg = f"Error during AI command selection or execution: {e}"
            raise click.ClickException(msg)

    except click.ClickException:
        # Re-raise ClickExceptions as they are intended to be shown to the user
        raise
    except Exception as e:
        # Catch other exceptions, log them, and raise a generic ClickException
        logger.error(f"An unexpected error occurred while analyzing code in {path}: {e}", exc_info=True)
        msg = f"An unexpected error occurred: {e}"
        raise click.ClickException(msg)


# Apply common options to all commands
for cmd in [pr_command, issue_command, analyze_code]:
    for option in reversed(get_common_options()):
        cmd = option(cmd)

if __name__ == "__main__":
    cli()
