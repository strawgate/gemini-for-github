from typing import Any

from fastmcp.client import Client
from fastmcp.client.transports import StdioTransport
from pydantic import Field

from gemini_for_github.errors.mcp import MCPServerDisabledError, MCPServerNotConnectedError, MCPServerNotInitializedError
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("mcp")


class MCPServer:
    """
    Manages a connection to a Model Context Protocol (MCP) server.
    It handles starting the server as a subprocess, verifying its readiness,
    and providing methods to interact with the server's tools.
    """

    client: Client

    def __init__(self, name: str, command: str, args: list[str], env: dict[str, str], disabled: bool):
        """Initializes the MCPServer instance.

        Args:
            name: The name of the MCP server.
            command: The command to execute to start the server.
            args: A list of arguments to pass to the server command.
            env: A dictionary of environment variables to set for the server process.
            disabled: A boolean indicating whether this server should be disabled.
        """
        self.name: str = name
        self.command: str = command
        self.args: list[str] = args
        self.env: dict[str, str] = env
        self.disabled: bool = disabled

    async def start(self):
        if self.disabled:
            msg = "Server is disabled"
            raise MCPServerDisabledError(msg)

        async with Client(
            StdioTransport(
                command=self.command,
                args=self.args,
                env=self.env,
            ),
        ) as client:
            self.client = client

    async def _verify_ready(self):
        """
        Checks if the MCP client is initialized, not disabled, and connected.
        Raises appropriate MCPServerError exceptions if any check fails.
        """
        if self.client is None:
            msg = "Client not initialized"
            raise MCPServerNotInitializedError(msg)
        if self.disabled:
            msg = "Server is disabled"
            raise MCPServerDisabledError(msg)
        if not self.client.is_connected():
            msg = "Client is not connected"
            raise MCPServerNotConnectedError(msg)

    async def ping(self):
        await self._verify_ready()
        return await self.client.ping()

    async def list_tools(self):
        await self._verify_ready()
        return await self.client.list_tools()

    async def call_tool(self, tool_name: str, tool_args: dict[str, str]):
        await self._verify_ready()
        return await self.client.call_tool(tool_name, tool_args)

    async def get_tools(self):
        await self._verify_ready()
        tools = await self.list_tools()

        for tool in tools:
            args: dict[str, Any] = Field(..., json_schema_extra=tool.inputSchema)

            def tool_function(tool_args: dict[str, Any] = args):
                return self.call_tool(tool.name, tool_args)

            tool_function.__name__ = tool.name
            tool_function.__doc__ = tool.description

        return {tool.name: tool_function for tool in tools}

    async def stop(self):
        await self._verify_ready()
        # await self.client()
