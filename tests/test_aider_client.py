

from pathlib import Path
from gemini_for_github.clients.aider import AiderClient
from aider.repomap import RepoMap

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model
from aider.repo import GitRepo

def test_aider_client():
    model = "gemini/gemini-2.5-flash-preview-04-17"
    aider = AiderClient(root=Path("."), model=model)
    assert aider is not None

    repo_map = aider.get_repo_map()

    assert repo_map is not None

