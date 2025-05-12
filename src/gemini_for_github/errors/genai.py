class GenAIClientError(Exception):
    """Base class for all errors related to the GenAI client.

    Attributes:
        message: The error message.
    """

    def __init__(self, message: str, *args: object) -> None:
        """Initializes the GenAIClientError.

        Args:
            message: The error message.
            *args: Additional arguments.
        """
        super().__init__(message, *args)


class GenAIToolFunctionNotFoundError(GenAIClientError):
    """Error raised when a tool function is not found.

    This occurs when the GenAI model attempts to call a tool function
    that is not defined or available in the client's tool registry.

    Example:
        >>> try:
        ...     client.generate_content(prompt, tools=[{'function_declarations': [{'name': 'non_existent_tool'}]}])
        ... except GenAIToolFunctionNotFoundError as e:
        ...     print(f"Tool function not found: {e}")
    """


class GenAIToolFunctionError(GenAIClientError):
    """Error raised when a tool function fails during execution.

    This indicates that a tool function called by the GenAI model
    raised an exception or returned an error status.

    Example:
        >>> try:
        ...     client.generate_content(prompt, tools=[{'function_declarations': [{'name': 'failing_tool'}]}])
        ... except GenAIToolFunctionError as e:
        ...     print(f"Tool function failed: {e}")
    """


class GenAITaskFailedError(GenAIClientError):
    """Error raised when a GenAI task fails to complete successfully.

    This can happen if the model encounters an internal error,
    fails to generate a response, or the generation process is interrupted.

    Example:
        >>> try:
        ...     client.generate_content(prompt)
        ... except GenAITaskFailedError as e:
        ...     print(f"GenAI task failed: {e}")
    """


class GenAITaskUnknownStatusError(GenAIClientError):
    """Error raised when a GenAI task has an unknown status.

    This occurs if the client receives an unexpected or unrecognized
    status code or message from the GenAI service.

    Example:
        >>> # Assuming a scenario where an API call returns an unexpected status
        >>> try:
        ...     client._make_api_call(...)
        ... except GenAITaskUnknownStatusError as e:
        ...     print(f"GenAI task has unknown status: {e}")
    """
