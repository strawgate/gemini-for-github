"""Basic logging configuration for the Gemini for GitHub application."""
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_LOGGER = logging.getLogger("gemini-for-github")
