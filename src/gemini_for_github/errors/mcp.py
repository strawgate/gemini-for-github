"""Custom exceptions for MCP server operations."""

class MCPServerError(Exception):
    """Base class for MCP server errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class MCPServerNotInitializedError(MCPServerError):
    """Error raised when MCP server is not initialized."""

    def __init__(self, message: str):
        super().__init__(message)


class MCPServerDisabledError(MCPServerError):
    """Error raised when MCP server is disabled."""

    def __init__(self, message: str):
        super().__init__(message)


class MCPServerNotConnectedError(MCPServerError):
    """Error raised when MCP server is not connected."""

    def __init__(self, message: str):
        super().__init__(message)
