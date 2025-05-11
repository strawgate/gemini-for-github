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
    A client to invoke Aider for code modifications.
    """

    def __init__(self, root: Path, model: str):
        self.root = root

        io = InputOutput(yes=True)
        self.model = Model(model)
        self.coder = Coder.create(
            main_model=self.model,
            io=io,
        )

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the Aider client."""
        return {
            "write_code": self.write_code,
        }

    def write_code(self, prompt: str) -> str:
        """
        Executes Aider with the given prompt.

        Args:
            prompt: The detailed prompt for Aider.
            model: Optional Aider model to use.
            on_branch: Optional branch to checkout before invoking Aider.

        Returns:
            A string containing the results.
        """
        logger.info(f"Invoking Aider with prompt: {prompt[:100]}...")

        try:
            result = self.coder.run(with_message=prompt)
        except Exception as e:
            msg = "Error invoking Aider with prompt: " + prompt
            logger.exception(msg)
            raise AiderError(msg) from e

        if result is None:
            msg = "Aider returned None"
            raise AiderNoneResultError(msg)

        return result
