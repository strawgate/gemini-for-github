import asyncio
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from string import Template

import asyncclick
import yaml
from pydantic import ValidationError

from gemini_for_github.clients.aider import AiderClient
from gemini_for_github.clients.filesystem import FileOperations, FolderOperations
from gemini_for_github.clients.genai import GenAIClient
from gemini_for_github.clients.git import GitClient
from gemini_for_github.clients.github import GitHubAPIClient
from gemini_for_github.clients.mcp import MCPServer
from gemini_for_github.config.config import Command, Config, ConfigFile
from gemini_for_github.errors.aider import AiderError
from gemini_for_github.errors.filesystem import FilesystemError
from gemini_for_github.errors.main import CommandNotFoundError, CommandNotSelectedError
from gemini_for_github.errors.mcp import MCPServerError
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("main")


async def _load_config(
    config_file_path: str, tool_restrictions: str | None, command_restrictions: str | None
) -> tuple[Config, ConfigFile]:
    """Loads and parses the application configuration."""
    with Path(config_file_path).open() as f:
        config_data = yaml.safe_load(f)
    config_file = ConfigFile(**config_data)

    split_tool_restrictions = tool_restrictions.split(",") if tool_restrictions else None
    split_command_restrictions = command_restrictions.split(",") if command_restrictions else None

    config = Config.from_config_file(
        config_file,
        tool_restrictions=split_tool_restrictions,
        command_restrictions=split_command_restrictions,
    )
    return config, config_file


async def _initialize_github_client(github_token: str, github_repo_id: int) -> tuple[GitHubAPIClient, dict[str, Callable]]:
    """Initializes and returns the GitHub API client and its tools."""
    github_client = GitHubAPIClient(token=github_token, repo_id=github_repo_id)
    return github_client, github_client.get_tools()


async def _initialize_git_client(repo_dir: Path, github_token: str, owner_repo: str) -> tuple[GitClient, dict[str, Callable]]:
    """Initializes and returns the Git client and its tools using the given repository path."""
    # TODO: The 'github_repo' parameter is currently unused by the GitClient constructor.
    # Investigate if it's needed or can be removed.
    git_client = GitClient(repo_dir=str(repo_dir), github_token=github_token, owner_repo=owner_repo)
    return git_client, git_client.get_tools()

async def _initialize_filesystem_client(root_path: Path) -> tuple[FileOperations, FolderOperations, dict[str, Callable]]:
    """Initializes and returns the Filesystem client and its tools."""
    file_operations = FileOperations(root_dir=root_path)
    folder_operations = FolderOperations(root_dir=root_path)
    return file_operations, folder_operations, {**file_operations.get_tools(), **folder_operations.get_tools()}


async def _initialize_genai_client(gemini_api_key: str, model: str) -> tuple[GenAIClient, dict[str, Callable]]:
    """Initializes and returns the GenAI client."""

    genai_client = GenAIClient(api_key=gemini_api_key, model=model)
    genai_tools = genai_client.get_tools()
    return genai_client, genai_tools


async def _initialize_aider_client(root_path: Path, model: str) -> tuple[AiderClient, dict[str, Callable]]:
    """Initializes and returns the Aider client and its tools."""
    aider_client = AiderClient(root=root_path, model=model)
    return aider_client, aider_client.get_tools()


async def _initialize_mcp_servers(config_file: ConfigFile) -> tuple[list[MCPServer], dict[str, Callable]]:
    """Initializes and returns a list of MCP servers and their aggregated tools based on the configuration."""
    mcp_servers = []
    tools = {}
    for server_config in config_file.mcp_servers:
        mcp_server = MCPServer(
            server_config.name, server_config.command, server_config.args, env=server_config.env, disabled=server_config.disabled
        )
        if not server_config.disabled:
            await mcp_server.start()
            mcp_servers.append(mcp_server)
            tools.update(await mcp_server.get_tools())

    return mcp_servers, tools


async def _select_command(user_question: str, commands: list[Command], genai_client: GenAIClient) -> Command:
    """Selects the most appropriate command based on the user's question."""
    system_prompt = f"""
    You are a GitHub based AI Agent. You receive plain text questions from the user and you need to determine which command, if any 
    most closely matches the user's request.

    Available Commands and when they are appropriate to use:
    {"- " + chr(10).join([f"{cmd.name}: Appropriate when the developer asks you to {cmd.description}" for cmd in commands])}

    Respond with nothing other than the name (key) of the command that most closely matches the user's request.
    """

    user_prompt = f"""
    User Request: **{user_question}**
    """

    logger.info(f"Calling Gemini for command selection... of {user_question}")

    command_selection_response = await genai_client.generate_content(system_prompt, [user_prompt], tools=[])
    selected_command_name = command_selection_response.get("text", "")

    if not selected_command_name:
        msg = f"Gemini did not select a command for {user_question}"
        raise CommandNotSelectedError(msg)

    selected_command_name = selected_command_name.strip()

    logger.info(f"Model selected command: {selected_command_name}")

    selected_command = next((cmd for cmd in commands if cmd.name == selected_command_name), None)

    if not selected_command:
        msg = f"Command '{selected_command_name}' not found"
        raise CommandNotFoundError(msg)

    return selected_command


async def _get_allowed_commands(config: Config, command_restrictions: str | None) -> list[Command]:
    """Gets the allowed commands from the config and CLI arguments."""
    allowed_commands = config.commands
    if command_restrictions:
        restricted_commands = command_restrictions.split(",")
        allowed_commands = [cmd for cmd in allowed_commands if cmd.name in restricted_commands]

    return allowed_commands


async def _execute_command(system_prompt: str, user_prompts: list[str], genai_client: GenAIClient, tools: list[Callable]) -> None:
    """Executes the selected command."""

    logger.info("Calling Gemini for prompt execution")
    final_response = await genai_client.generate_content(system_prompt, user_prompts, tools=tools)  # type: ignore
    logger.info("Gemini believes it has completed the task.")


@asyncclick.command()
@asyncclick.option("--github-token", type=str, required=True, envvar="GITHUB_TOKEN", help="GitHub API token")
@asyncclick.option("--github-repo", type=str, required=True, envvar="GITHUB_REPO", help="GitHub repository owner/name")
@asyncclick.option("--github-repo-id", type=int, required=True, envvar="GITHUB_REPO_ID", help="GitHub repository ID")
@asyncclick.option("--gemini-api-key", type=str, required=True, envvar="GEMINI_API_KEY", help="Gemini API key")
@asyncclick.option("--github-issue-number", type=int, envvar="GITHUB_ISSUE_NUMBER", default=None, help="GitHub issue number")
@asyncclick.option("--github-pr-number", type=int, envvar="GITHUB_PR_NUMBER", default=None, help="GitHub pull request number")
@asyncclick.option("--model", type=str, default="gemini-2.5-flash-preview-04-17", envvar="GEMINI_MODEL", help="Gemini model to use")
@asyncclick.option("--config-file", type=str, default=None, envvar="CONFIG_FILE", help="Path to the config file")
@asyncclick.option(
    "--tool-restrictions", type=str, default=None, envvar="TOOL_RESTRICTIONS", help="Comma-separated list of tool restrictions"
)
@asyncclick.option(
    "--command-restrictions", type=str, default=None, envvar="COMMAND_RESTRICTIONS", help="Comma-separated list of command restrictions"
)
@asyncclick.option("--debug", is_flag=True, default=False, envvar="DEBUG", help="Enable debug mode")
@asyncclick.option("--user-question", type=str, required=True, envvar="USER_QUESTION", help="The user's natural language question")
async def cli(
    github_token: str,
    github_repo: str,
    github_repo_id: int,
    gemini_api_key: str,
    github_issue_number: int | None,
    github_pr_number: int | None,
    model: str,
    config_file: str | None,
    tool_restrictions: str | None,
    command_restrictions: str | None,
    debug: bool,
    user_question: str,
):
    """
    Main command-line interface for the Gemini for GitHub AI Agent.

    This script loads configuration, initializes clients (GitHub, Git, GenAI, etc.),
    selects an appropriate command based on user input, and executes it.
    It handles GitHub issue/PR context and tool/command restrictions.
    """
    try:
        root_path = Path.cwd()

        if debug:
            BASE_LOGGER.setLevel(logging.DEBUG)

        script_dir = Path(__file__).parent
        config_path = config_file if config_file else script_dir / "config" / "default.yaml"
        config, _ = await _load_config(str(config_path), tool_restrictions, command_restrictions)

        tools = {}
        github_client, github_tools = await _initialize_github_client(github_token, github_repo_id)
        tools.update(github_tools)

        repo_dir = root_path / "repo"

        git_client, git_tools = await _initialize_git_client(repo_dir, github_token, github_repo)
        tools.update(git_tools)

        file_operations, folder_operations, filesystem_tools = await _initialize_filesystem_client(root_path)
        tools.update(filesystem_tools)

        aider_client, aider_tools = await _initialize_aider_client(repo_dir, model)
        tools.update(aider_tools)

        # mcp_servers, mcp_tools = await _initialize_mcp_servers(config_file)
        # tools.update(mcp_tools)

        genai_client, genai_tools = await _initialize_genai_client(gemini_api_key, model)
        tools.update(genai_tools)

        command = await _select_command(user_question, config.commands, genai_client)

        command_tools = [tools[tool] for tool in command.allowed_tools]
        command_tool_names = list(command.allowed_tools)
        command_tool_names.sort()
        
        context = {}
        if github_issue_number:
            context["github_issue_number"] = github_issue_number
        if github_pr_number:
            context["github_pr_number"] = github_pr_number
        if user_question:
            context["user_question"] = user_question

        user_prompt = []

        if command.example_flow:
            user_prompt.append(f"\nExample Flow for resolving this request: {command.example_flow}")

        template_string = Template(command.prompt)
        user_prompt.append(template_string.substitute(context))

        system_prompt = config.system_prompt
        logger.info(f"Answering user question: {user_question} with tools: {command_tool_names}")

        response = await _execute_command(system_prompt, user_prompt, genai_client, command_tools)

        logger.info(f"Response: {response}")

    except (FileNotFoundError, yaml.YAMLError, ValidationError):
        logger.exception("Configuration error")
        sys.exit(1)
    except (FilesystemError, AiderError, MCPServerError, CommandNotFoundError):
        logger.exception("An application error occurred")
        sys.exit(1)
    except Exception:
        logger.exception("An unexpected error occurred")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(cli())
