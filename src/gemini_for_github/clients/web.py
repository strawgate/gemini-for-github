from collections.abc import Callable

import requests
from html_to_markdown import convert_to_markdown

from gemini_for_github.errors.web import WebClientConversionError, WebClientFetchError, WebClientUnknownError
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("web_client")


class WebClient:
    """
    A client for fetching HTML content from a URL and converting it to Markdown.

    This client uses the `requests` library to fetch web content and
    `html_to_markdown` to perform the conversion. It's useful for obtaining
    a simplified textual representation of a web page, often for an LLM to process.
    """

    def __init__(self):
        """Initializes the WebClient."""
        logger.info("WebClient initialized")

    def get_tools(self) -> dict[str, Callable]:
        """
        Retrieves the callable methods of this client intended to be used as tools.

        This is typically used to register the client's web fetching capabilities
        with a tool-using system.

        Returns:
            dict[str, Callable]: A dictionary mapping tool names to the corresponding
                                 bound methods of this client instance.
                                 Example: {'get_web_page': <bound method WebClient.get_web_page of ...>}
        """
        return {
            "get_web_page": self.get_web_page,
        }

    def get_web_page(self, url: str) -> str:
        """
        Fetches the content of a web page and converts it to Markdown.

        Args:
            url: The URL of the web page to fetch.

        Returns:
            The content of the web page converted to Markdown.
        """
        logger.info(f"Fetching web page: {url}")
        html_content: str
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            html_content = response.text
        except requests.exceptions.RequestException as e:
            msg = f"Error fetching web page {url}: {type(e).__name__} - {e}"
            logger.exception(msg)
            raise WebClientFetchError(msg) from e
        except Exception as e: # Catch any other unexpected error during fetch
            msg = f"An unexpected error occurred while fetching {url}: {type(e).__name__} - {e}"
            logger.exception(msg)
            raise WebClientUnknownError(msg) from e

        try:
            markdown_content = convert_to_markdown(html_content)
        except Exception as e:
            msg = f"Error converting HTML to Markdown for {url}"
            logger.exception(msg)
            raise WebClientConversionError(msg) from e

        logger.info(f"Successfully fetched and converted {url}")
        return markdown_content
