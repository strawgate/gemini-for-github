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
            # "clone_repository": self.clone_repository,
        }

    def configure_git(self) -> bool:
        """Configure the Git client."""
        with self.error_handler("configuring git", f"branch name: {self.repo.active_branch.name}", GitConfigError):
            self.repo.config_writer().set_value("user", "name", "gemini-for-github").release()
            self.repo.config_writer().set_value("user", "email", "gemini-for-github@strawgate.com").release()

        return True

    def clone_repository(self, branch: str = "main", overwrite: bool = True) -> bool:
        """
        Clones a Git repository from the configured URL into the specified directory.

        Use this to initialize the local repository if it doesn't exist or needs to be refreshed.
        It handles removing an existing directory if `overwrite` is True and changes the
        current working directory (`os.chdir`) to the repository root after cloning.
        It also configures the default Git user name and email after cloning.

        Args:
            branch (str): The specific branch to clone. Defaults to "main".
            overwrite (bool): If True, deletes the existing `repo_dir` before cloning.
                              If False, cloning will likely fail if the directory exists and is not empty.
                              Defaults to True.

        Returns:
            bool: True if cloning and configuration are successful.

        Raises:
            GitCloneError: If the cloning process fails (e.g., invalid URL, branch not found, network issues).
            GitConfigError: If configuring the user name/email fails after cloning.
            GitClientError: For other unexpected errors during the process.
        """

        if overwrite and Path(self.repo_dir).exists():
            shutil.rmtree(self.repo_dir)
            os.makedirs(self.repo_dir)

        with self.error_handler("cloning repository", f"repository URL: {self.owner_repo}, branch: {branch}", GitCloneError):
            self.repo = Repo.clone_from(self.repo_url, self.repo_dir, branch=branch)
            self.origin = self.repo.remotes.origin
            os.chdir(self.repo_dir)
            logger.info(f"Changing directory to {self.repo_dir}")

        self.configure_git()

        return True

    def new_branch(self, name: str):
        """
        Creates and checks out a new local branch starting from the current HEAD.

        Use this tool to create a new branch for development or feature work. It also sets up
        the new local branch to track a remote branch of the same name (even if the remote
        branch doesn't exist yet - it will be created on the first push).

        Args:
            name (str): The desired name for the new branch.

        Raises:
            GitBranchExistsError: If a local branch with the given `name` already exists.
            GitNewBranchError: If there's an error during the branch creation or checkout process.
            GitConfigError: If configuring the user name/email fails after creating the branch.
            GitClientError: For other unexpected errors.
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
        Pushes the current local branch to the remote 'origin'.

        Use this tool to publish your local changes on the current branch to the remote
        repository. It pushes the current branch to a remote branch with the same name.
        It ensures Git user configuration is set before attempting the push.

        Raises:
            GitPushError: If the push operation fails (e.g., authentication error, network issue,
                          conflicts if the remote branch has diverged and requires a pull first).
            GitConfigError: If configuring the user name/email fails before pushing.
            GitClientError: For other unexpected errors.
        """
        logger.info("Pushing branch to origin")

        self.configure_git()

        with self.error_handler("pushing branch to origin", f"branch name: {self.repo.active_branch.name}", GitPushError):
            self.origin.push(refspec=f"{self.repo.active_branch.name}:{self.repo.active_branch.name}")
