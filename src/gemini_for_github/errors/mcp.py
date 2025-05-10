
class MCPServerError(Exception):
    """Base class for MCP server errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class MCPServerNotInitializedError(MCPServerError):
    """Error raised when MCP server is not initialized."""

    def __init__(self, message: str):
        super().__init__(message)
