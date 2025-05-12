from pathlib import Path

from gemini_for_github.clients.aider import AiderClient


def test_aider_client():
    model = "gemini/gemini-2.5-flash-preview-04-17"
    aider = AiderClient(root=Path(), model=model)
    assert aider is not None

    repo_map = aider.get_repo_map()

    assert repo_map is not None

def test_aider_client_run():
    model = "gemini/gemini-2.5-flash-preview-04-17"
    aider = AiderClient(root=Path(), model=model)
    assert aider is not None

    repo_map = aider.write_code(prompt="/diff")

    assert repo_map is not None
