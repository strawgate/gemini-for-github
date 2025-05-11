import pytest
import requests_mock

from src.gemini_for_github.clients.web import WebClient


@pytest.fixture
def web_client():
    """Fixture to provide a WebClient instance."""
    return WebClient()


def test_get_web_page_success(web_client, requests_mock):
    """Tests successful fetching and markdown conversion of a web page."""
    url = "http://example.com"
    html_content = "<html><body><h1>Test Page</h1><p>This is a test.</p></body></html>"
    expected_markdown = "# Test Page\n\nThis is a test."

    requests_mock.get(url, text=html_content)

    markdown_output = web_client.get_web_page(url)

    assert markdown_output.strip() == expected_markdown.strip()

# Add more tests here as needed, e.g., for error handling, different content types, etc.
