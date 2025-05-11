from collections.abc import Callable
from pathlib import Path

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model
from aider.repo import GitRepo

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
        self.model = Model(f"gemini/{model}")

        self.root = root

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the Aider client."""
        return {
            "write_code": self.write_code,
            "offer_code": self.offer_code_diff,
        }


    def offer_code_diff(self, prompt: str) -> str:
        """
        Executes Aider, an advanced coding assistant with the given prompt and returns the diff

        Args:
            prompt: The detailed prompt for Aider.
            diff_when_done: The diff from Aider's work
        Returns:
            A string containing the results of the Aider execution.
        """

        io = InputOutput(yes=True)

        repo = GitRepo(io, [], str(self.root), models=[self.model])
        self.coder: Coder = Coder.create(
            main_model=self.model,
            io=io,
            repo=repo,
        )
        self.coder.verbose = True

        logger.info(f"Invoking Aider in {self.root}, cwd: {Path.cwd()} with prompt: {prompt[:100]}...")

        try:
            self.coder.run(with_message=prompt)
            result = self.coder.run(with_message="/diff")
        except Exception as e:
            msg = "Error invoking Aider with prompt: " + prompt
            logger.exception(msg)
            raise AiderError(msg) from e

        if result is None:
            msg = "Aider returned None"
            raise AiderNoneResultError(msg)

        return result

    def write_code(self, prompt: str, commit_when_done: bool = True) -> str:
        """
        Executes Aider, an advanced coding assistant with the given prompt.

        Args:
            prompt: The detailed prompt for Aider.
            commit_when_done: Whether to commit the changes when done.
        Returns:
            A string containing the results of the Aider execution.
        """

        io = InputOutput(yes=True)

        repo = GitRepo(io, [], str(self.root), models=[self.model])
        self.coder: Coder = Coder.create(
            main_model=self.model,
            io=io,
            repo=repo,
        )
        self.coder.verbose = True

        logger.info(f"Invoking Aider in {self.root}, cwd: {Path.cwd()} with prompt: {prompt[:100]}...")

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
