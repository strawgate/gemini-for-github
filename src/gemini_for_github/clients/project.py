from collections.abc import Callable
from pathlib import Path

from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("project")


class ProjectClient:
    """
    A client for project-specific operations, currently focused on reading README files.

    This client provides utilities that might be specific to understanding or interacting
    with the structure or documentation of a software project. It includes limits on the
    number of READMEs read and their individual sizes to prevent excessive memory usage.
    """
    def __init__(self):
        """Initializes the ProjectClient."""
        pass

    def get_tools(self) -> dict[str, Callable]:
        """
        Retrieves the callable methods of this client intended to be used as tools.

        This is typically used to register the client's project-related capabilities
        with a tool-using system.

        Returns:
            dict[str, Callable]: A dictionary mapping tool names to the corresponding
                                 bound methods of this client instance.
                                 Example: {'read_readmes': <bound method ProjectClient.read_readmes of ...>}
        """
        return {
            "read_readmes": self.read_readmes,
        }

    def read_readmes(self) -> dict[str, str]:
        """
        Scans the current working directory for Markdown files (`*.md`) at the root,
        and then recursively in subdirectories, reading their content.

        Use this tool to gather documentation or important textual information
        typically found in README files or other Markdown documents within a project.
        It prioritizes root-level Markdown files first.

        Limits:
        - Reads a maximum of 100 README files in total.
        - Truncates the content of individual files to 1024 characters if they are larger,
          logging a warning for truncated files.

        Returns:
            dict[str, str]: A dictionary where keys are the file names (e.g., "README.md")
                            and values are the string contents of those files (potentially truncated).
                            Example:
                            ```python
                            {
                                "README.md": "# Project Title\n\nThis is the main readme...",
                                "CONTRIBUTING.md": "# How to Contribute\n\nGuidelines..."
                            }
                            ```
        """
        readmes = {}

        # Start with root readmes
        # Using Path.cwd() to be explicit about the starting point.
        for file in Path.cwd().glob("*.md"):
            if len(readmes) >= 100:  # noqa: PLR2004
                logger.info("Reached maximum limit of 100 READMEs. Stopping root scan.")
                break
            try:
                with open(file, encoding="utf-8") as f:
                    content = f.read()
                if len(content) > 1024:  # noqa: PLR2004
                    logger.warning(f"README '{file.name}' is too large (>1KB), truncating.")
                    readmes[file.name] = content[:1024]
                else:
                    readmes[file.name] = content
            except Exception as e:
                logger.error(f"Could not read root README '{file.name}': {e}")


        # Then scan subdirectories for other Markdown files
        for file in Path.cwd().glob("**/*.md"):
            if len(readmes) >= 100:  # noqa: PLR2004
                logger.info("Reached maximum limit of 100 READMEs. Stopping recursive scan.")
                break
            
            if file.name in readmes: # Avoid re-reading root files already processed
                continue
            
            try:
                with open(file, encoding="utf-8") as f:
                    content = f.read()
                if len(content) > 1024:  # noqa: PLR2004
                    logger.warning(f"README '{file.name}' is too large (>1KB), truncating.")
                    readmes[file.name] = content[:1024]
                else:
                    readmes[file.name] = content
            except Exception as e:
                logger.error(f"Could not read subdirectory README '{file.name}': {e}")
        

        return readmes
