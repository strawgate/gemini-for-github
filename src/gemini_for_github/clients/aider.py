from collections.abc import Callable
import json
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

    repo_map: str | None = None
    file_structure: list[str]
    structured_file_structure: dict[str, list[str]]
    structured_repo_map: dict[str, list[tuple[int, str]]]
    inverse_structured_repo_map: dict[str, list[tuple[str, int, str]]]

    def __init__(self, root: Path, model: str):
        """Initializes the AiderClient.

        Args:
            root: The root directory for Aider's operations.
            model: The specific Gemini model string to be used by Aider (e.g., "gemini/gemini-2.5-flash-preview-04-17").
        """
        self.root = Path("action_testing/repo")

        self.model = Model(
            f"gemini/{model}",
            editor_edit_format="diff-fenced",
        )

        io = InputOutput(yes=True)

        repo = GitRepo(io, [], root, models=[self.model])

        self.coder: Coder = Coder.create(
            main_model=self.model,
            io=io,
            repo=repo,
        )

        self.coder.repo_map.max_map_tokens = 200000

        self.file_structure = []
        self.structured_file_structure = {}

        self.structured_repo_map = {}
        """File -> Module-level vars, classes, functions"""

        self.inverse_structured_repo_map = {}
        """Module-level vars, classes, functions -> File"""


    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the Aider client."""
        return {
            "write_code": self.write_code,
            "offer_code": self.offer_code_diff,
            "search_repo_map": self.search_repo_map,
            "get_code_structure": self.get_code_structure,
        }
    
    def search_repo_map(self, search_terms: list[str]) -> list[tuple[str, int, str]]:
        """
        Search for classes, functions, or comments using search terms.

        Args:
            search_terms: A list of terms to search for.

        Returns:
            A list of tuples containing the file, line number, and line content for each match.

        Example:
        ```python
        search_terms = ["kafka", "producer", "consumer"]
        results = aider_client.search_repo_map(search_terms)
        ```
        """

        if self.repo_map is None:
            self.get_structured_repo_map()

        results = []

        for line, matches in self.inverse_structured_repo_map.items():
            if any(term in line for term in search_terms):
                results.extend(matches)

        return results

    def get_code_structure(self) -> dict[str, list[tuple[int, str]]]:
        """
        Get the code structure of the repository.
        """
        if self.repo_map is None:
            self.get_structured_repo_map()

        return self.structured_file_structure

    def get_structured_repo_map(self) -> list[str]:
        """
        Structure the repo map into a more readable format.
        """
        
        if not self.coder.repo_map:
            msg = "Could not get repo map."
            raise AiderError(msg)

        self.repo_map = self.coder.get_repo_map() # type: ignore
        tree_context_cache = self.coder.repo_map.tree_context_cache

        for file, entry in tree_context_cache.items():
            context = entry["context"]
            if not context:
                continue

            lines_of_interest = context.lines_of_interest
            if not lines_of_interest:
                continue

            shown_lines = context.show_lines
            if not shown_lines:
                continue

            lines = lines_of_interest

            interesting_detailed_lines: list[tuple[int, str]] = [
                (line_no, context.lines[line_no])
                for line_no in {*lines, *shown_lines}
            ]

            self.structured_repo_map[file] = interesting_detailed_lines

            # Store more full chunks when we get asked for a file name
            interesting_lines: list[tuple[int, str]] = [
                (line_no, context.lines[line_no])
                for line_no in lines
            ]
            # Store smaller chunks for our inverse lookup
            for line_no, line in interesting_lines:

                if line not in self.inverse_structured_repo_map:
                    self.inverse_structured_repo_map[line] = []

                # Get the five lines before and after the line of interest
                text_chunk = "\n".join(context.lines[line_no-5:line_no+5])

                self.inverse_structured_repo_map[line].append((file, line_no, text_chunk))

            # Generate a flat list of files for our file structure
            self.file_structure.append(file)

            file_path_parts = file.split("/")
            file_name = file_path_parts[-1]
            file_dir = "/".join(file_path_parts[:-1])

            if file_dir not in self.structured_file_structure:
                self.structured_file_structure[file_dir] = []

            self.structured_file_structure[file_dir].append(file_name)


        repo_map_size = len(json.dumps(self.repo_map))
        file_structure_size = len(json.dumps(self.file_structure))
        structured_file_structure_size = len(json.dumps(self.structured_file_structure))
        structured_repo_map_size = len(json.dumps(self.structured_repo_map))
        inverse_structured_repo_map_size = len(json.dumps(self.inverse_structured_repo_map))
        return self.file_structure



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
