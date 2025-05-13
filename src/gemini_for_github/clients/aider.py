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
        self.model = Model(
            f"gemini/{model}",
            editor_edit_format="diff-fenced",
        )

        self.root = root

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the Aider client."""
        return {
            "write_code": self.write_code,
            "offer_code": self.offer_code_diff,
            "get_repo_map": self.get_repo_map,
        }

    def get_repo_map(self) -> str:
        """
        Generates and retrieves the repository map used by Aider.

        The repo map provides Aider with context about the file structure and potentially
        key symbols within the repository, helping it understand the codebase better.
        Use this when you need Aider to have an up-to-date understanding of the project layout.

        Returns:
            str: A textual representation of the repository map. The exact format depends
                 on Aider's implementation but typically includes file paths and structure.
                 Example (simplified):
                 "src/main.py:\n  func1()\n  ClassA:\n    method1()\nREADME.md"

        Raises:
            AiderError: If the repo map generation fails.
        """

        io = InputOutput(yes=True)

        repo = GitRepo(io, [], str(self.root), models=[self.model])
        self.coder: Coder = Coder.create(
            main_model=self.model,
            io=io,
            repo=repo,
        )

        repo_map = self.coder.get_repo_map(force_refresh=True)

        if repo_map is None:
            raise AiderError("Failed to get repo map")

        if len(repo_map) > 1048576:  # noqa: PLR2004
            logger.warning(f"Repo map is too large (>1MB) to be processed: {len(repo_map)} characters.")
            return repo_map[:1048576]  # noqa: PLR2004

        return repo_map

    def offer_code_diff(self, prompt: str) -> str:
        """
        Executes Aider with a prompt and returns the proposed code changes as a diff.

        This function runs Aider with the provided instructions but specifically requests
        the diff output (`/diff`) instead of applying changes directly. Use this when you
        want to preview the changes Aider suggests based on a prompt before deciding
        whether to apply them.

        Args:
            prompt: The detailed natural language instructions for the desired code changes.

        Returns:
            str: A diff string representing the changes suggested by Aider.
                 Example:
                 ```diff
                 --- a/src/gemini_for_github/clients/aider.py
                 +++ b/src/gemini_for_github/clients/aider.py
                 @@ -60,10 +75,19 @@
                  def offer_code_diff(self, prompt: str) -> str:
                      \"\"\"
                      Executes Aider, an advanced coding assistant with the given prompt and returns the diff
+
+                     This function runs Aider with the provided instructions but specifically requests
+                     the diff output (`/diff`) instead of applying changes directly. Use this when you
+                     want to preview the changes Aider suggests based on a prompt before deciding
+                     whether to apply them.

                      Args:
                          prompt: The detailed prompt for Aider.
-                         diff_when_done: The diff from Aider's work
+
                      Returns:
-                         A string containing the results of the Aider execution.
+                         A diff string representing the changes suggested by Aider.
+                         Example:
+                         ```diff
+                         --- a/file.py
+                         +++ b/file.py
+                         @@ -1,1 +1,2 @@
+                          print("hello")
+                         +print("world")
+
+                         ```
                      \"\"\"

                      io = InputOutput(yes=True)

                 ```

        Raises:
            AiderError: If there's an error during Aider execution.
            AiderNoneResultError: If Aider returns None unexpectedly.
        """

        io = InputOutput(yes=True)

        repo = GitRepo(io, [], str(self.root), models=[self.model])
        self.coder: Coder = Coder.create(
            main_model=self.model,
            io=io,
            repo=repo,
        )
        #self.coder.verbose = True

        logger.info(f"Invoking Aider in {self.root}, cwd: {Path.cwd()} with prompt: {prompt[:1000]}...")

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
        Executes Aider with a prompt, allowing it to apply code changes directly.

        Use this function to instruct Aider to perform code modifications based on the
        provided prompt. Aider will attempt to understand the request, generate the
        necessary code changes, and apply them to the files in the repository.

        A prefix is added to the prompt instructing Aider to act as a senior developer
        and critically evaluate the given instructions before proceeding.

        Args:
            prompt: The detailed natural language instructions for the desired code changes.
            commit_when_done: If True, Aider will attempt to automatically commit the
                              applied changes using `/commit`. Defaults to True.

        Returns:
            str: A string containing the results or logs from the Aider execution,
                 which might include confirmation of applied changes, file modifications,
                 or commit messages if `commit_when_done` is True.

        Raises:
            AiderError: If there's an error during Aider execution.
            AiderNoneResultError: If Aider returns None unexpectedly.
        """

        io = InputOutput(yes=True)

        repo = GitRepo(io, [], str(self.root), models=[self.model])
        self.coder: Coder = Coder.create(
            main_model=self.model,
            edit_format="diff-fenced",
            io=io,
            repo=repo,
        )
        self.coder.verbose = True

        prompt_prefix = """
You are a senior developer. You will be given pretty specific instructions to complete a task. The person who prepared these instructions
may not have fully understood the task, or may have made some mistakes. It is your job to review the instructions and make sure they are
correct. If other work is required to actually complete the task you will do that.
"""

        logger.info(f"Invoking Aider in {self.root}, cwd: {Path.cwd()} with prompt prefix (not shown) and prompt: {prompt[:100]}...")

        final_prompt = prompt_prefix + prompt

        try:
            result = self.coder.run(with_message=final_prompt)
            if commit_when_done:
                self.coder.run(with_message="/commit")
        except Exception as e:
            msg = "Error invoking Aider with prompt: " + prompt
            logger.exception(msg)
            raise AiderError(msg) from e

        if result is None:
            msg = "Aider returned None"
            raise AiderNoneResultError(msg)

        return result
