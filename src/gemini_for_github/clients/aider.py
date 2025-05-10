import logging

import git
from aider.coders import Coder

logger = logging.getLogger(__name__)


class AiderTool:
    """
    A tool to invoke Aider for code modifications.
    """

    def __init__(self):
        pass

    def run(self, instruction: str, files_to_include: list[str], model: str | None = None) -> dict:
        """
        Executes Aider with the given instruction and files.

        Args:
            instruction: The detailed prompt for Aider.
            files_to_include: A list of file paths Aider should be aware of/edit.
            model: Optional Aider model to use.

        Returns:
            A dictionary containing the results, including diff, new branch name, and commit SHA.
        """
        logger.info(f"Invoking Aider with instruction: {instruction[:100]}...")
        logger.info(f"Files to include: {files_to_include}")
        logger.info(f"Model: {model}")

        try:
            coder = Coder(
                fnames=files_to_include,
                model=model,
            )

            diffstat, response_text = coder.run(instruction)

            new_branch_name = "aider-generated-branch"
            commit_sha = "unknown"

            if coder.repo:
                try:
                    current_branch = coder.repo.active_branch
                    new_branch_name = current_branch.name
                    latest_commit = coder.repo.head.commit
                    commit_sha = latest_commit.hexsha
                    logger.info(f"Aider committed changes to branch: {new_branch_name}, commit SHA: {commit_sha}")
                except git.InvalidGitRepositoryError:
                    logger.warning("Aider Coder was not initialized with a Git repository. Cannot determine branch/commit.")
                except Exception as git_e:
                    logger.error(f"Error inspecting Git repository after Aider run: {git_e}")
            else:
                logger.warning("Aider Coder has no associated Git repository. Cannot determine branch/commit.")

            results = {
                "success": True,
                "diff": diffstat,
                "response_text": response_text,
                "new_branch_name": new_branch_name,
                "commit_sha": commit_sha,
                "error": None,
            }
            logger.info(f"Aider invocation successful. Branch: {new_branch_name}, Commit: {commit_sha}")

        except Exception as e:
            logger.error(f"Error during Aider invocation: {e}")
            results = {"success": False, "diff": "", "response_text": "", "new_branch_name": "", "commit_sha": "", "error": str(e)}

        return results


if __name__ == "__main__":
    aider_tool = AiderTool()

    result = aider_tool.run(
        instruction="Refactor the main function to improve readability.",
        files_to_include=["src/gemini_for_github/main.py"],
        model="gpt-4o",
    )
    print(result)
