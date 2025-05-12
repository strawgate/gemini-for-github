from collections.abc import Callable

import requests
from html_to_markdown import convert_to_markdown

from gemini_for_github.errors.web import WebClientConversionError, WebClientFetchError, WebClientUnknownError
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("web_client")


class WebClient:
    """
    A client for fetching web content and converting it to Markdown.
    """

    def __init__(self):
        """Initializes the WebClient."""
        logger.info("WebClient initialized")

    def get_tools(self) -> dict[str, Callable]:
        """Returns a dictionary of available tools."""
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
            msg = f"Error fetching web page {url}"
            logger.exception(msg)
            raise WebClientFetchError(msg) from e
        except Exception as e:
            msg = f"An unexpected error occurred while processing {url}"
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
