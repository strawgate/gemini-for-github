class WebClientError(Exception):
    """Base class for web client errors."""


class WebClientFetchError(WebClientError):
    """Error fetching web page."""


class WebClientConversionError(WebClientError):
    """Error converting HTML to Markdown."""


class WebClientUnknownError(WebClientError):
    """Unknown error."""
