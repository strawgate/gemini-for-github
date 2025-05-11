import os
import shutil
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

from git import RemoteReference, Repo

from gemini_for_github.errors.git import (
    GitBranchExistsError,
    GitClientError,
    GitCloneError,
    GitConfigError,
    GitNewBranchError,
    GitPushError,
)
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("git")


class GitClient:
    """
    A client to invoke Git for code modifications.
    """

    def __init__(self, repo_dir, github_token: str, owner_repo: str):
        self.repo_dir = repo_dir
        self.owner_repo = owner_repo
        self.repo_url = f"https://x-access-token:{github_token}@github.com/{owner_repo}.git"

    @contextmanager
    def error_handler(self, operation: str, details: str, exception: type[Exception] | None = None):
        """
        A context manager for handling common Git errors.
        It wraps Git operations and raises specific GitClientError
        subclasses for known issues, or a generic GitClientError for unknown exceptions.

        Args:
            operation: The operation being performed, used for logging.
            details: A descriptive message for the generic GitClientError.
        """
        try:
            logger.info(f"Performing {operation} for {details}")
            yield
            logger.info(f"Successfully performed {operation} for {details}")
        except GitClientError as e:
            logger.exception(f"Error occurred while performing {operation}: {details}")
            raise e from e
        except Exception as e:
            logger.exception(f"Unknown error occurred while {operation}: {details}")
            if exception:
                raise exception from e
            raise GitClientError(details) from e

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the Git client."""
        return {
            "new_branch": self.new_branch,
            "push_current_branch": self.push_current_branch,
            "clone_repository": self.clone_repository,
        }

    def configure_git(self) -> bool:
        """Configure the Git client."""
        with self.error_handler("configuring git", f"branch name: {self.repo.active_branch.name}", GitConfigError):
            self.repo.config_writer().set_value("user", "name", "gemini-for-github").release()
            self.repo.config_writer().set_value("user", "email", "gemini-for-github@strawgate.com").release()

        return True

    def clone_repository(self, branch: str = "main", overwrite: bool = True) -> bool:
        """
        Clones a repository from a given URL.

        Args:
            branch: The branch to clone.
            overwrite: Defaults to true, the repository will be cloned even if it already exists.

        Returns:
            True if the repository was cloned successfully, False otherwise.
        """

        if overwrite and Path(self.repo_dir).exists():
            shutil.rmtree(self.repo_dir)

        with self.error_handler("cloning repository", f"repository URL: {self.repo_url}, branch: {branch}", GitCloneError):
            self.repo = Repo.clone_from(self.repo_url, self.repo_dir, branch=branch)
            self.origin = self.repo.remotes.origin
            os.chdir(self.repo_dir)
            logger.info(f"Changing directory to {self.repo_dir}")

        # list out all files in the repository recursively
        for root, dirs, files in os.walk(self.repo_dir):
            for file in files:
                logger.info(f"File: {os.path.join(root, file)}")

        self.configure_git()

        return True

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

        with self.error_handler("creating new branch", f"branch name: {name}", GitNewBranchError):
            self.repo.head.reference = self.repo.create_head(name)
            rem_ref = RemoteReference(self.repo, f"refs/remotes/{self.origin.name}/{name}")
            self.repo.head.reference.set_tracking_branch(rem_ref)
            self.repo.head.reference.checkout()

        self.configure_git()

    def push_current_branch(self):
        """
        Pushes the current branch to the origin.
        """
        logger.info("Pushing branch to origin")

        self.configure_git()

        with self.error_handler("pushing branch to origin", f"branch name: {self.repo.active_branch.name}", GitPushError):
            self.origin.push(refspec=f"{self.repo.active_branch.name}:{self.repo.active_branch.name}")
