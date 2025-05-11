from collections.abc import Callable

from git import Remote, RemoteReference, Repo

from gemini_for_github.errors.git import GitBranchExistsError
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("git")


class GitClient:
    """
    A client to invoke Git for code modifications.
    """

    def __init__(self, repo_path: str = "."):
        self.repo: Repo = Repo(repo_path)
        self.origin: Remote = self.repo.remotes.origin
        self.starting_branch: str = self.repo.active_branch.name

        # self.head: Head | None = None

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the Git client."""
        return {
            "new_branch": self.new_branch,
            "push": self.push,
        }

    def return_to_starting_branch(self):
        """
        Returns to the starting branch.
        """
        logger.info(f"Returning to starting branch: {self.starting_branch}")
        self.repo.head.reference = self.repo.create_head(self.starting_branch)

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

        self.repo.head.reference = self.repo.create_head(name)
        rem_ref = RemoteReference(self.repo, f"refs/remotes/{self.origin.name}/{name}")
        self.repo.head.reference.set_tracking_branch(rem_ref)
        self.repo.head.reference.checkout()

    def push(self):
        """
        Pushes the given branch to the origin.
        """
        logger.info("Pushing branch to origin")
        self.origin.push()
