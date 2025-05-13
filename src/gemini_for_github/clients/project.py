from collections.abc import Callable
from pathlib import Path

from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("project")


class ProjectClient:
    def __init__(self):
        pass

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the Project client."""
        return {
            "read_readmes": self.read_readmes,
        }

    def read_readmes(self) -> dict[str, str]:
        readmes = {}

        # start with root readmes
        for file in Path().glob("*.md"):
            if len(readmes) > 100:  # noqa: PLR2004
                break

            with open(file) as f:
                readmes[file.name] = f.read()  # noqa: PLR2004
            if len(readmes[file.name]) > 1024:  # noqa: PLR2004
                logger.warning(f"README is too large (>1KB) to be included in read_readmes: {file.name}")
                readmes[file.name] = readmes[file.name][:1024]  # noqa: PLR2004

        for file in Path().glob("**/*.md"):
            if len(readmes) > 100:  # noqa: PLR2004
                break
            
            if file.name in readmes:
                continue

            with open(file) as f:
                readmes[file.name] = f.read()  # noqa: PLR2004

            if len(readmes[file.name]) > 1024:  # noqa: PLR2004
                logger.warning(f"README is too large (>1KB) to be included in read_readmes: {file.name}")
                readmes[file.name] = readmes[file.name][:1024]  # noqa: PLR2004

        

        return readmes
