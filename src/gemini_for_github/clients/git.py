from collections.abc import Callable

from git import Remote, RemoteReference, Repo

from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("git")


class GitClient:
    """
    A client to invoke Git for code modifications.
    """

    def __init__(self, repo_path: str = "."):
        self.repo: Repo = Repo(repo_path)
        self.origin: Remote = self.repo.remotes.origin
        # self.head: Head | None = None

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the Git client."""
        return {
            "new_branch": self.new_branch,
            "push": self.push,
        }

    def new_branch(self, name: str):
        """
        Creates a new branch with the given name.
        """
        self.repo.head.reference = self.repo.create_head(name)
        rem_ref = RemoteReference(self.repo, f"refs/remotes/{self.origin.name}/{name}")
        self.repo.head.reference.set_tracking_branch(rem_ref)
        self.repo.head.reference.checkout()

    def push(self):
        """
        Pushes the given branch to the origin.
        """
        self.origin.push()
