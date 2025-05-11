from collections.abc import Callable
import os

from git import Remote, RemoteReference, Repo

from gemini_for_github.errors.git import GitBranchExistsError, GitNewBranchError, GitPushError
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("git")


class GitClient:
    """
    A client to invoke Git for code modifications.
    """

    def __init__(self, repo_dir, github_token: str, owner_repo: str):
        self.repo_dir = repo_dir
        self.repo_url = f"https://{github_token}@github.com/{owner_repo}.git"

    def set_safe_directory(self):
        """
        Set the safe directory for the Git client.
        """
        self.repo.git.config("safe.directory", "*")

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the Git client."""
        return {
            "new_branch": self.new_branch,
            "push_current_branch": self.push_current_branch,
            "clone_repository": self.clone_repository,
        }


    def clone_repository(self, branch: str = "main"):
        """
        Clones a repository from a given URL.
        """
        logger.info(f"Cloning repository from {self.repo_url} to {self.repo_dir}")
        self.repo = Repo.clone_from(self.repo_url, self.repo_dir, branch=branch)
        self.origin = self.repo.remotes.origin

        logger.info(f"Changing directory to {self.repo_dir}")
        os.chdir(self.repo_dir)

    def new_branch(self, name: str):
        """
        Creates a new branch with the given name.
        """
        logger.info(f"Creating new branch: {name}")

        # check if branch already exists
        if name in self.repo.heads:
            msg = f"Branch {name} already exists"
            logger.info(msg)
            raise GitBranchExistsError(msg)

        try:
            self.repo.head.reference = self.repo.create_head(name)
            rem_ref = RemoteReference(self.repo, f"refs/remotes/{self.origin.name}/{name}")
            self.repo.head.reference.set_tracking_branch(rem_ref)
            self.repo.head.reference.checkout()
        except Exception as e:
            msg = f"Error creating new branch: {e}"
            logger.exception(msg)
            raise GitNewBranchError(msg) from e

    def push_current_branch(self):
        """
        Pushes the current branch to the origin.
        """
        logger.info("Pushing branch to origin")
        try:
            self.origin.push(refspec=f"{self.repo.active_branch.name}:{self.repo.active_branch.name}")
        except Exception as e:
            msg = f"Error pushing branch to origin: {e}"
            logger.exception(msg)
            raise GitPushError(msg) from e
