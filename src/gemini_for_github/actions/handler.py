import functools
import logging
from collections.abc import Callable
from typing import Any

from google.genai.types import GoogleSearch
from google.genai.types import Tool as GoogleTool
from mcp import Tool as MCPTool

from src.gemini_for_github.clients.genai_client import GenAIClient
from src.gemini_for_github.clients.github_api_client import GitHubAPIClient
from src.gemini_for_github.config.prompt_manager import PromptManager
from src.gemini_for_github.mcp_integration.mcp_client_manager import MCPClientManager
from src.gemini_for_github.tools.aider_tool import AiderTool
from src.gemini_for_github.tools.filesystem_tools import get_file_info
from src.gemini_for_github.tools.github_tools import (
    create_github_pull_request,
    create_issue_comment,
    create_pr_review,
    get_issue_body,
    get_pull_request_diff,
)

logger = logging.getLogger(__name__)


class ActionHandler:
    """Handler for executing AI-powered actions, relying on SDK for tool calls."""

    def __init__(
        self,
        ai_model: GenAIClient,
        github_api: GitHubAPIClient,
        prompt_manager: PromptManager,
        mcp_client_manager: MCPClientManager,
    ):
        self.ai_model = ai_model
        self.github_api = github_api
        self.prompt_manager = prompt_manager
        self.mcp_client_manager = mcp_client_manager
        self.tools: list[Callable[..., Any] | GoogleTool] = []

        google_search_tool = GoogleTool(google_search=GoogleSearch())
        self.tools.append(google_search_tool)

        github_tool_functions_to_wrap = {
            "get_pull_request_diff": get_pull_request_diff,
            "get_issue_body": get_issue_body,
            "create_pr_review": create_pr_review,
            "create_issue_comment": create_issue_comment,
            "create_github_pull_request": create_github_pull_request,
        }
        for name, func in github_tool_functions_to_wrap.items():
            wrapped_func = functools.partial(func, self.github_api)
            wrapped_func.__name__ = name
            wrapped_func.__doc__ = func.__doc__
            self.tools.append(wrapped_func)

        if get_file_info:
            self.tools.append(get_file_info)

        aider_tool_instance = AiderTool()
        if hasattr(aider_tool_instance, "run") and callable(aider_tool_instance.run):
            self.tools.append(aider_tool_instance.run)
        else:
            logger.error("AiderTool does not have a callable 'run' method.")

        mcp_tools_with_server: list[tuple[str, MCPTool]] = self.mcp_client_manager.get_all_tools_with_server()
        for server_name, mcp_tool_obj in mcp_tools_with_server:

            def create_mcp_wrapper(s_name: str, mcp_t: MCPTool) -> Callable[..., Any]:
                async def mcp_wrapper(**kwargs: Any) -> Any:
                    logger.info(
                        f"SDK calling dynamically generated wrapper for MCP tool: {mcp_t.name} on server {s_name} with args: {kwargs}",
                    )
                    return await self.mcp_client_manager.call_mcp_tool(s_name, mcp_t.name, arguments=kwargs)

                mcp_wrapper.__name__ = mcp_t.name
                mcp_wrapper.__doc__ = mcp_t.description
                return mcp_wrapper

            wrapper_function = create_mcp_wrapper(server_name, mcp_tool_obj)
            self.tools.append(wrapper_function)
            logger.info(f"Registered MCP tool '{mcp_tool_obj.name}' as a callable Python tool.")

    async def execute(
        self,
        action: str,
        **kwargs: Any,  # Allow any additional keyword arguments for prompt formatting
    ) -> str:
        """
        Executes an action by generating content with the AI model,
        relying on the GenAI SDK to handle all tool calls automatically.
        """
        initial_prompt_text = self.prompt_manager.get_prompt(action, **kwargs)

        logger.info(
            f"Executing action '{action}' with prompt. Tools available to SDK: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in self.tools]}",
        )

        try:
            response = await self.ai_model.generate_content(
                contents=[{"role": "user", "parts": [{"text": initial_prompt_text}]}],
                tools=self.tools,
            )
            final_text_response = response.text

            if final_text_response is None:
                logger.warning(f"Final response text for action '{action}' was None. Returning empty string.")
                final_text_response = ""

            logger.info(f"Action '{action}' executed. Final LLM response: {final_text_response[:200]}...")
            return final_text_response

        except Exception as e:
            logger.error(f"Error during AI model generation or SDK tool processing for action '{action}': {e}", exc_info=True)
            return f"Error processing action '{action}': {e}"
