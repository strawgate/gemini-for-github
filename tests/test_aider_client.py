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

def test_aider_repo_map():
    model = "gemini/gemini-2.5-flash-preview-04-17"
    aider = AiderClient(root=Path(), model=model)
    assert aider is not None

    file_structure = aider.get_structured_repo_map()

    assert file_structure is not None

    interesting_lines = aider.search_repo_map(search_terms=["kafka", "producer", "consumer"])

    assert interesting_lines is not None