class WebClientError(Exception):
    """Base class for web client errors.

    Attributes:
        message: The error message.
    """


class WebClientFetchError(WebClientError):
    """Error fetching web page.

    This exception is raised when there is an issue retrieving content
    from a URL, such as network errors, invalid URLs, or server issues.

    Example:
        >>> import requests
        >>> try:
        ...     response = requests.get("http://invalid.url")
        ...     response.raise_for_status()
        ... except requests.RequestException as e:
        ...     raise WebClientFetchError(f"Failed to fetch URL: {e}")
    """


class WebClientConversionError(WebClientError):
    """Error converting HTML to Markdown.

    This occurs when there is a problem parsing HTML content or
    transforming it into Markdown format.

    Example:
        >>> # Assuming a function `html_to_markdown`
        >>> invalid_html = "<p>Invalid <tag>"
        >>> try:
        ...     markdown = html_to_markdown(invalid_html)
        ... except Exception as e: # Catch specific parsing errors if possible
        ...     raise WebClientConversionError(f"Failed to convert HTML to Markdown: {e}")
    """


class WebClientUnknownError(WebClientError):
    """Unknown error in the web client.

    This is a generic fallback exception for unexpected errors
    that do not fit into more specific categories.

    Example:
        >>> # Assuming a web client operation
        >>> try:
        ...     client.some_operation()
        ... except Exception as e:
        ...     # If the error is not a known WebClientError subclass
        ...     if not isinstance(e, WebClientError):
        ...         raise WebClientUnknownError(f"An unexpected error occurred: {e}") from e
        ...     else:
        ...         raise # Re-raise known WebClientErrors
    """
