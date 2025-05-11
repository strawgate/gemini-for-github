import logging
from typing import Callable

import requests
from html_to_markdown import convert
from vertexai.generative_models import Tool

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
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            html_content = response.text
            markdown_content = convert(html_content)
            logger.info(f"Successfully fetched and converted {url}")
            return markdown_content
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching web page {url}: {e}")
            return f"Error fetching web page {url}: {e}"
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing {url}: {e}")
            return f"An unexpected error occurred while processing {url}: {e}"
