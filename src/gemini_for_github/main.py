import asyncio
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from string import Template

import asyncclick
from gemini_for_github.clients.project import ProjectClient
import yaml
from pydantic import ValidationError
from google.genai.types import (
    Content,
    ContentListUnion,
    ContentUnion,
    FunctionCall,
    FunctionCallingConfig,
    FunctionCallingConfigMode,
    FunctionDeclaration,
    FunctionResponse,
    GenerateContentConfig,
    GenerateContentResponse,
    GoogleSearch,
    HarmBlockThreshold,
    HarmCategory,
    Part,
    SafetySetting,
    ThinkingConfig,
    Tool,
    ToolConfig,
)
from gemini_for_github.clients.aider import AiderClient
from gemini_for_github.clients.filesystem import FileOperations, FolderOperations
from gemini_for_github.clients.gemini import GenAIClient, GenAITaskResult, GenAITaskSuccess
from gemini_for_github.clients.git import GitClient
from gemini_for_github.clients.github import GitHubAPIClient
from gemini_for_github.clients.mcp import MCPServer
from gemini_for_github.clients.web import WebClient
from gemini_for_github.config.config import Command, Config, ConfigFile
from gemini_for_github.errors.aider import AiderError
from gemini_for_github.errors.filesystem import FilesystemError
from gemini_for_github.errors.main import CommandNotFoundError, CommandNotSelectedError
from gemini_for_github.errors.mcp import MCPServerError
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("main")

async def _load_config(config_file_path: str, tool_restrictions: str | None, command_restrictions: str | None) -> tuple[Config, ConfigFile]:
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


async def _initialize_github_client(github_token: str, github_repo_id: int) -> GitHubAPIClient:
    """Initializes and returns the GitHub API client."""
    return GitHubAPIClient(token=github_token, repo_id=github_repo_id)


async def _initialize_git_client(repo_dir: Path, github_token: str, owner_repo: str) -> GitClient:
    """Initializes and returns the Git client using the given repository path."""
    return GitClient(repo_dir=str(repo_dir), github_token=github_token, owner_repo=owner_repo)


async def _initialize_filesystem_client(root_path: Path) -> tuple[FileOperations, FolderOperations]:
    """Initializes and returns the Filesystem client."""
    file_operations = FileOperations(root_dir=root_path)
    folder_operations = FolderOperations(root_dir=root_path)
    return file_operations, folder_operations


async def _initialize_genai_client(gemini_api_key: str, model: str, thinking: bool) -> GenAIClient:
    """Initializes and returns the GenAI client."""
    return GenAIClient(api_key=gemini_api_key, model=model, thinking=thinking)


async def _initialize_aider_client(root_path: Path, model: str) -> AiderClient:
    """Initializes and returns the Aider client."""
    return AiderClient(root=root_path, model=model)


async def _initialize_mcp_servers(config_file: ConfigFile) -> list[MCPServer]:
    """Initializes and returns a list of MCP servers based on the configuration."""
    mcp_servers = []
    for server_config in config_file.mcp_servers:
        mcp_server = MCPServer(
            server_config.name, server_config.command, server_config.args, env=server_config.env, disabled=server_config.disabled
        )
        if not server_config.disabled:
            await mcp_server.start()
            mcp_servers.append(mcp_server)

    return mcp_servers


async def _select_command(user_question: str, commands: list[Command], genai_client: GenAIClient) -> Command:
    """Selects the most appropriate command based on the user's question."""
    system_prompt = """
    You are a GitHub based AI Agent. You receive plain text questions from the developer and you need to determine which
    command, if any most closely matches the developer's request. 
    
    You are not trying to solve the developer's problem. Just categorize their request.
    
    When you identify the command name that most closely matches the developer's request:
    1. Report successful completion
      a. Place the command_name in the "task_details" field
      b. Place a detailed description of why this command is appropriate in the "completion_details" field

    If you cannot identify a command name that most closely matches the developer's request:
    1. Call the "get_issue_with_comments" tool to get the issue details and comments to help you identify the command name
    2. If you still cannot identify a command name, report failure
      a. Place a detailed explanation of why none of the commands are appropriate in the "failure_details" field
    """

    user_prompt = f"""
    Request to identify the best command to use for: **{user_question}**
    """

    available_commands = f"""
- {"\n- ".join([f"{cmd.name}: Appropriate when the developer asks you to {cmd.description}" for cmd in commands])}
"""

    content_list = [
        genai_client.new_model_content("Ok, I understand, i'm not solving the problem, just picking the best command to use."),
        genai_client.new_user_content(available_commands),
        genai_client.new_model_content("Okay I have read the available commands and I understand that I may need to get info from the github issue via the get_issue_with_comments tool if the user's question is too vague."),
        genai_client.new_user_content(user_prompt),
    ]

    logger.info(f"Calling Gemini for command selection... of {user_question}. Allowed commands: {', '.join([cmd.name for cmd in commands])}")

    if response := await genai_client.perform_task(system_prompt, content_list, allowed_tools=["get_issue_with_comments"]):
        
        if isinstance(response, GenAITaskSuccess):
            command_selection_response = response.task_details
        else:
            raise CommandNotSelectedError(response.failure_details)

        logger.info(f"Gemini selected command: {command_selection_response} {response.completion_details}")

        selected_command = next((cmd for cmd in commands if cmd.name == command_selection_response), None)
        if not selected_command:
            msg = f"Command '{selected_command}' not found"
            raise CommandNotFoundError(msg)

        logger.info(f"Gemini selected command: {selected_command}")

        return selected_command

    msg = f"Gemini did not select a command for {user_question}: {response}"

    raise CommandNotSelectedError(msg)


async def _execute_command(system_prompt: str, content_list: list[Content], genai_client: GenAIClient, tools: list[str]) -> GenAITaskResult:
    """Executes the selected command."""
    logger.info(f"Calling Gemini for prompt execution. Content list contains {len(content_list)} items")
    return await genai_client.perform_task(system_prompt, content_list, allowed_tools=tools)

def prepare_repository(git_client: GitClient, github_client: GitHubAPIClient, pr_number: int | None = None):
    """Prepares the repository for the command."""

    branch: str = github_client.get_default_branch()

    if pr_number:
        branch = github_client.get_branch_from_pr(pull_number=pr_number)
        logger.info(f"Cloning repository {branch} for pull request {pr_number}")
    else:
        logger.info(f"Cloning repository {branch} for default branch")
    
    git_client.clone_repository(branch=branch)


@asyncclick.command()
@asyncclick.option("--github-token", type=str, required=True, envvar="GITHUB_TOKEN", help="GitHub API token")
@asyncclick.option("--github-repo", type=str, required=True, envvar="GITHUB_REPO", help="GitHub repository owner/name")
@asyncclick.option("--github-repo-id", type=int, required=True, envvar="GITHUB_REPO_ID", help="GitHub repository ID")
@asyncclick.option("--gemini-api-key", type=str, required=True, envvar="GEMINI_API_KEY", help="Gemini API key")
@asyncclick.option("--github-issue-number", type=int, envvar="GITHUB_ISSUE_NUMBER", default=None, help="GitHub issue number")
@asyncclick.option("--github-pr-number", type=int, envvar="GITHUB_PR_NUMBER", default=None, help="GitHub pull request number")
@asyncclick.option("--model", type=str, default="gemini-2.5-flash-preview-04-17", envvar="GEMINI_MODEL", help="Gemini model to use")
@asyncclick.option("--thinking", type=bool, default=True, envvar="THINKING", help="Enable thinking mode")
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
    thinking: bool,
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

        # Initialize clients
        github_client = await _initialize_github_client(github_token, github_repo_id)
        repo_dir = root_path / "repo"
        git_client = await _initialize_git_client(repo_dir, github_token, github_repo)
        file_operations, folder_operations = await _initialize_filesystem_client(root_path)
        aider_client = await _initialize_aider_client(repo_dir, model)
        web_client = WebClient()
        genai_client = await _initialize_genai_client(gemini_api_key, model, thinking)

        project_client = ProjectClient()

        # Register tools with GenAI client
        for name, func in github_client.get_tools().items():
            genai_client.register_tool(name, func)
        for name, func in git_client.get_tools().items():
            genai_client.register_tool(name, func)
        for name, func in file_operations.get_tools().items():
            genai_client.register_tool(name, func)
        for name, func in folder_operations.get_tools().items():
            genai_client.register_tool(name, func)
        for name, func in aider_client.get_tools().items():
            genai_client.register_tool(name, func)
        for name, func in web_client.get_tools().items():
            genai_client.register_tool(name, func)
        for name, func in project_client.get_tools().items():
            genai_client.register_tool(name, func)

        command = await _select_command(user_question, config.commands, genai_client)

        prepare_repository(git_client, github_client, github_pr_number)

        context = {}
        if github_issue_number:
            context["github_issue_number"] = github_issue_number
        if github_pr_number:
            context["github_pr_number"] = github_pr_number
        if user_question:
            context["user_question"] = user_question
    
        content_list: list = []

        if command.prerun_tools:
            content_list.append(genai_client.new_model_content("Before I get started with the user's request, I'm going to get some background information."))
            for tool in command.prerun_tools:
                content_list.append(genai_client.new_model_function_call(FunctionCall(name=tool, args={})))
                result = await genai_client._handle_function_call(tool, {})
                content_list.append(genai_client.new_model_function_response(FunctionResponse(name=tool, response=result.response)))
            content_list.append(genai_client.new_model_content("I've got the background information I need. Let's get started on the user's request."))

        template_string = Template(command.prompt)
        content_list.append(genai_client.new_user_content(template_string.substitute(context)))

        if command.example_flow:
            content_list.append(genai_client.new_model_content("What flow should I follow for answering this request?"))
            content_list.append(genai_client.new_user_content(f"\nExample Flow for resolving this request: {command.example_flow}"))
            content_list.append(genai_client.new_model_content("I've got the example flow. Let's get started on the user's request."))

        system_prompt = config.system_prompt
        logger.info(f"Answering user question: {user_question}")

        final_response = await _execute_command(system_prompt, content_list, genai_client, command.allowed_tools)

        if isinstance(final_response, GenAITaskSuccess):
            logger.info(f"Gemini believes it has completed the task: {final_response.task_details}: {final_response.completion_details}")
        else:
            logger.info(f"Gemini believes it has failed the task: {final_response.task_details}: {final_response.failure_details}")

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
