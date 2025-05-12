"""Custom exceptions for Model Context Protocol (MCP) server operations."""


class MCPServerError(Exception):
    """Base class for MCP server errors.

    Attributes:
        message: The error message.
    """

    def __init__(self, message: str):
        """Initializes the MCPServerError.

        Args:
            message: The error message.
        """
        self.message = message
        super().__init__(self.message)


class MCPServerNotInitializedError(MCPServerError):
    """Error raised when MCP server is not initialized.

    This occurs when an operation requiring an initialized MCP server
    is attempted before the server has been properly set up or started.

    Example:
        >>> # Assuming `server` is an MCPServer instance
        >>> if not server.is_initialized():
        ...     raise MCPServerNotInitializedError("MCP server has not been initialized.")
    """

    def __init__(self, message: str):
        """Initializes the MCPServerNotInitializedError.

        Args:
            message: The error message.
        """
        super().__init__(message)


class MCPServerDisabledError(MCPServerError):
    """Error raised when MCP server is disabled.

    This exception is raised when an attempt is made to interact with
    an MCP server instance that has been explicitly marked as disabled.

    Example:
        >>> # Assuming `server` is an MCPServer instance
        >>> if server.is_disabled():
        ...     raise MCPServerDisabledError("MCP server is currently disabled.")
    """

    def __init__(self, message: str):
        """Initializes the MCPServerDisabledError.

        Args:
            message: The error message.
        """
        super().__init__(message)


class MCPServerNotConnectedError(MCPServerError):
    """Error raised when MCP server is not connected.

    This indicates that a connection to the MCP server is required for
    an operation, but the client is not currently connected.

    Example:
        >>> # Assuming `server` is an MCPServer instance
        >>> if not server.is_connected():
        ...     raise MCPServerNotConnectedError("Not connected to the MCP server.")
    """

    def __init__(self, message: str):
        """Initializes the MCPServerNotConnectedError.

        Args:
            message: The error message.
        """
        super().__init__(message)
