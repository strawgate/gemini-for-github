from collections.abc import Callable
from pathlib import Path


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
        for file in Path().glob("**/*.md"):
            with open(file) as f:
                readmes[file.name] = f.read()

        return readmes
