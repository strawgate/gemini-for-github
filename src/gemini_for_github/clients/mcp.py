from typing import Any

from fastmcp.client import Client
from fastmcp.client.transports import StdioTransport
from pydantic import Field

from gemini_for_github.errors.mcp import MCPServerDisabledError, MCPServerNotConnectedError, MCPServerNotInitializedError
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("mcp")


class MCPServer:
    client: Client

    def __init__(self, name: str, command: str, args: list[str], env: dict[str, str], disabled: bool):
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


# Sample from Github that works but we will implement differently here
# The below uses uv package manager to define script dependencies
# Assumes `server_config.json` is in the same folder.
# run with 'uv run [scriptname].py'
# /// script
# dependencies = [
#   "fastmcp",
# ]
# ///

# {
#   "mcpServers": {
#     "sqlite": {
#       "command": "uvx",
#       "args": [
#         "mcp-server-sqlite",
#         "--db-path",
#         "test.db"
#       ]
#     },
#     "tavily-mcp": {
#       "command": "npx",
#       "args": [
#         "-y",
#         "tavily-mcp@0.1.4"
#       ],
#       "env": {
#         "TAVILY_API_KEY": "your-api-key-here"
#       },
#       "disabled": false,
#       "autoApprove": []
#     }
#   }
# }

# from fastmcp import Client
# from fastmcp.client.transports import StdioTransport
# import asyncio
# import json
# import os

# async def test_mcp_server(server_name, config):
#     """Test a single MCP server based on its configuration."""
#     print(f"\n{'='*50}")
#     print(f"Testing MCP server: {server_name}")
#     print(f"{'='*50}")

#     # Skip disabled servers
#     if config.get("disabled", False):
#         print(f"Server {server_name} is disabled, skipping...")
#         return f"Server {server_name} is disabled"

#     # Set up environment variables if specified
#     env = os.environ.copy()
#     if "env" in config:
#         env.update(config["env"])

#     # Connect to the server
#     async with Client(StdioTransport(
#         command=config["command"],
#         args=config["args"],
#         env=env
#     )) as client:
#         # Test basic connectivity
#         print("Testing connectivity...")
#         ping_result = await client.ping()
#         print(f"Ping result: {ping_result}")

#         # List available tools
#         print("\nListing available tools...")
#         try:
#             tools = await client.list_tools()
#             # Handle Tool objects properly
#             tool_info = []
#             for tool in tools:
#                 # Extract relevant attributes from Tool objects
#                 tool_data = {
#                     "name": getattr(tool, "name", "unknown"),
#                     "description": getattr(tool, "description", ""),
#                     "parameters": getattr(tool, "parameters", {})
#                 }
#                 tool_info.append(tool_data)
#             print(f"Available tools: {json.dumps(tool_info, indent=2)}")

#             # Store tools for later use
#             return_data = {"tools": tool_info}
#         except Exception as e:
#             print(f"Error listing tools: {e}")
#             return_data = {"error": str(e)}

#         # List available resources
#         print("\nListing available resources...")
#         try:
#             resources = await client.list_resources()
#             # Handle Resource objects properly
#             resource_info = []
#             for resource in resources:
#                 # Extract relevant attributes from Resource objects
#                 resource_data = {
#                     "name": getattr(resource, "name", "unknown"),
#                     "description": getattr(resource, "description", ""),
#                     "type": getattr(resource, "type", "unknown")
#                 }
#                 resource_info.append(resource_data)
#             print(f"Available resources: {json.dumps(resource_info, indent=2)}")
#             return_data["resources"] = resource_info
#         except Exception as e:
#             print(f"Error listing resources: {e}")

#         # Try to call a tool (if any are available)
#         if tools:
#             try:
#                 # Get the name attribute from the Tool object
#                 tool_name = getattr(tools[0], "name", None)
#                 if tool_name:
#                     print(f"\nTrying to call tool: {tool_name}...")
#                     result = await client.call_tool(tool_name, {"test": "parameter"})
#                     print(f"Tool result: {result}")
#                     return_data["tool_test"] = {"name": tool_name, "result": result}
#             except Exception as e:
#                 print(f"Error calling tool: {e}")

#         # Try to get a prompt (if supported)
#         print("\nTrying to get a prompt...")
#         try:
#             greeting = await client.get_prompt("welcome", {"name": "Tester"})
#             print(f"Prompt result: {greeting}")
#             return_data["prompt_test"] = greeting
#         except Exception as e:
#             print(f"Error getting prompt: {e}")

#         return {server_name: return_data}

# async def test_all_mcp_servers():
#     """Test all MCP servers defined in the configuration file."""
#     # Load server configuration
#     try:
#         with open("server_config.json", "r") as f:
#             config = json.load(f)
#     except Exception as e:
#         print(f"Error loading server_config.json: {e}")
#         return {"error": f"Failed to load configuration: {str(e)}"}

#     # Get MCP servers configuration
#     mcp_servers = config.get("mcpServers", {})
#     if not mcp_servers:
#         print("No MCP servers defined in configuration")
#         return {"error": "No MCP servers defined"}

#     # Test each server
#     results = {}
#     for server_name, server_config in mcp_servers.items():
#         try:
#             result = await test_mcp_server(server_name, server_config)
#             results.update(result if isinstance(result, dict) else {server_name: result})
#         except Exception as e:
#             print(f"Error testing server {server_name}: {e}")
#             results[server_name] = {"error": str(e)}

#     return results

# # Run the async function
# if __name__ == "__main__":
#     print("Starting MCP client tests...")
#     try:
#         results = asyncio.run(test_all_mcp_servers())
#         print(f"\nFinal results summary:")
#         print(json.dumps(results, indent=2))
#     except Exception as e:
#         print(f"Error in main execution: {e}")
