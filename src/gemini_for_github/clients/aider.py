from collections.abc import Callable
from pathlib import Path

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model

from gemini_for_github.errors.aider import AiderError, AiderNoneResultError
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("aider")


class AiderClient:
    """
    A client for interacting with the Aider tool, which facilitates AI-driven code modifications.
    This client initializes and manages the Aider Coder instance.
    """

    def __init__(self, root: Path, model: str):
        """Initializes the AiderClient.

        Args:
            root: The root directory for Aider's operations.
            model: The specific Gemini model string to be used by Aider (e.g., "gemini/gemini-2.5-flash-preview-04-17").
        """
        self.root = root

        io = InputOutput(yes=True, root=str(self.root))
        self.model = Model(f"gemini/{model}")
        self.coder: Coder = Coder.create(
            main_model=self.model,
            io=io,
        )

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the Aider client."""
        return {
            "write_code": self.write_code,
        }

    def write_code(self, prompt: str, commit_when_done: bool = True) -> str:
        """
        Executes Aider with the given prompt.

        Args:
            prompt: The detailed prompt for Aider.
            commit_when_done: Whether to commit the changes when done.
        Returns:
            A string containing the results of the Aider execution.
        """
        logger.info(f"Invoking Aider in {self.root} with prompt: {prompt[:100]}...")

        try:
            result = self.coder.run(with_message=prompt)
            if commit_when_done:
                result = self.coder.run(with_message="/commit")
        except Exception as e:
            msg = "Error invoking Aider with prompt: " + prompt
            logger.exception(msg)
            raise AiderError(msg) from e

        if result is None:
            msg = "Aider returned None"
            raise AiderNoneResultError(msg)

        return result
