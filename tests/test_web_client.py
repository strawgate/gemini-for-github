import pytest
import requests_mock  # noqa: F401

from gemini_for_github.clients.web import WebClient


@pytest.fixture
def web_client():
    """Fixture to provide a WebClient instance."""
    return WebClient()


def test_get_web_page_success(web_client, requests_mock):  # noqa: F811
    """Tests successful fetching and markdown conversion of a web page."""
    url = "http://example.com"
    html_content = "<html><body><h1>Test Page</h1><p>This is a test.</p></body></html>"
    expected_markdown = "Test Page\n=========\n\nThis is a test."

    requests_mock.get(url, text=html_content)

    markdown_output = web_client.get_web_page(url)

    assert markdown_output.strip() == expected_markdown.strip()


def test_get_web_page_multiple_paragraphs(web_client, requests_mock):
    """Tests fetching and markdown conversion of a page with multiple paragraphs."""
    url = "http://example.com/paragraphs"
    html_content = "<html><body><p>First paragraph.</p><p>Second paragraph.</p></body></html>"
    expected_markdown = "First paragraph.\n\nSecond paragraph."

    requests_mock.get(url, text=html_content)

    markdown_output = web_client.get_web_page(url)

    assert markdown_output.strip() == expected_markdown.strip()


def test_get_web_page_with_list(web_client, requests_mock):  # noqa: F811
    """Tests fetching and markdown conversion of a page with a list."""
    url = "http://example.com/list"
    html_content = "<html><body><h1>List</h1><ul><li>Item 1</li><li>Item 2</li></ul></body></html>"
    expected_markdown = "List\n====\n\n* Item 1\n* Item 2"

    requests_mock.get(url, text=html_content)

    markdown_output = web_client.get_web_page(url)

    assert markdown_output.strip() == expected_markdown.strip()


# Add more tests here as needed, e.g., for error handling, different content types, etc.
