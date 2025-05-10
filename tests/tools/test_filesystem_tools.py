import os
from unittest.mock import patch

from src.tools.filesystem_tools import find_files, get_file_info, list_directory, read_file, read_files, read_files_by_extension, write_file

# Mock data for filesystem operations
MOCK_FILE_STRUCTURE = {
    "test_dir": {"file1.txt": "content of file1", "file2.md": "content of file2", "subdir": {"file3.py": "content of file3"}},
    "another_dir": {"file4.txt": "content of file4"},
}


def mock_os_walk(top, topdown=True, onerror=None, followlinks=False):
    """Mock os.walk."""
    for root, _dirs, _files in os.walk(top, topdown, onerror, followlinks):
        relative_root = os.path.relpath(root, ".")
        if relative_root == ".":
            relative_root = ""

        current_dir = MOCK_FILE_STRUCTURE
        for part in relative_root.split(os.sep):
            if part and part in current_dir:
                current_dir = current_dir[part]
            elif part:
                current_dir = {}  # Directory not in mock structure

        mock_dirs = [d for d in current_dir if isinstance(current_dir[d], dict)]
        mock_files = [f for f in current_dir if isinstance(current_dir[f], str)]

        yield root, mock_dirs, mock_files


def mock_path_exists(path):
    """Mock Path.exists()."""
    parts = Path(path).parts
    current = MOCK_FILE_STRUCTURE
    for part in parts:
        if part in current:
            current = current[part]
        else:
            return False
    return True


def mock_path_is_file(path):
    """Mock Path.is_file()."""
    parts = Path(path).parts
    current = MOCK_FILE_STRUCTURE
    for part in parts:
        if part in current:
            current = current[part]
        else:
            return False
    return isinstance(current, str)


def mock_path_is_dir(path):
    """Mock Path.is_dir()."""
    parts = Path(path).parts
    current = MOCK_FILE_STRUCTURE
    for part in parts:
        if part in current:
            current = current[part]
        else:
            return False
    return isinstance(current, dict)


def mock_path_iterdir(path):
    """Mock Path.iterdir()."""
    parts = Path(path).parts
    current = MOCK_FILE_STRUCTURE
    for part in parts:
        if part in current:
            current = current[part]
        else:
            return []  # Directory not in mock structure

    mock_items = []
    for name, content in current.items():
        mock_item_path = Path(path) / name
        mock_item = Mock()
        mock_item.name = name
        mock_item.is_dir.return_value = isinstance(content, dict)
        mock_item.is_file.return_value = isinstance(content, str)
        mock_item.relative_to.return_value = mock_item_path  # Simplified relative path
        mock_items.append(mock_item)
    return mock_items


def mock_path_read_text(path):
    """Mock Path.read_text()."""
    parts = Path(path).parts
    current = MOCK_FILE_STRUCTURE
    for part in parts:
        if part in current:
            current = current[part]
        else:
            raise FileNotFoundError  # File not in mock structure
    if isinstance(current, str):
        return current
    raise IsADirectoryError  # Path is a directory


def mock_path_write_text(path, content):
    """Mock Path.write_text()."""
    # In a real scenario, you might update the MOCK_FILE_STRUCTURE here
    # For this mock, we just simulate success
    return


def mock_path_rglob(pattern):
    """Mock Path.rglob()."""
    # This is a simplified mock and might not handle all glob patterns
    matching_files = []
    for root, _, files in os.walk(".", topdown=True):
        for file in files:
            file_path = Path(root) / file
            if file_path.match(pattern):
                matching_files.append(file_path)
    return matching_files


def mock_path_stat(path):
    """Mock Path.stat()."""
    # Return a mock stat object with basic attributes
    mock_stat = Mock()
    mock_stat.st_size = 100  # Dummy size
    mock_stat.st_mtime = 1678886400  # Dummy modified time
    return mock_stat


@patch("src.tools.filesystem_tools.Path.exists", side_effect=mock_path_exists)
@patch("src.tools.filesystem_tools.Path.iterdir", side_effect=mock_path_iterdir)
@patch("src.tools.filesystem_tools.Path.cwd", return_value=Path("."))
def test_list_directory(mock_cwd, mock_iterdir, mock_exists):
    """Test list_directory tool function."""
    path = "test_dir"
    result = list_directory(path)
    expected = [
        {"name": "file1.txt", "type": "file", "path": "test_dir/file1.txt"},
        {"name": "file2.md", "type": "file", "path": "test_dir/file2.md"},
        {"name": "subdir", "type": "directory", "path": "test_dir/subdir"},
    ]
    # Sort results for consistent comparison
    result.sort(key=lambda x: x["name"])
    expected.sort(key=lambda x: x["name"])
    assert result == expected


@patch("src.tools.filesystem_tools.Path.rglob", side_effect=mock_path_rglob)
@patch("src.tools.filesystem_tools.Path.is_file", side_effect=mock_path_is_file)
@patch("src.tools.filesystem_tools.Path.read_text", side_effect=mock_path_read_text)
@patch("src.tools.filesystem_tools.Path.cwd", return_value=Path("."))
@patch("os.walk", side_effect=mock_os_walk)
def test_read_files(mock_os_walk, mock_cwd, mock_read_text, mock_is_file, mock_rglob):
    """Test read_files tool function."""
    pattern = "*.txt"
    start_dir = "test_dir"
    result = read_files(pattern, start_dir)
    expected = {"test_dir/file1.txt": "content of file1"}
    assert result == expected


@patch("src.tools.filesystem_tools.read_files")
def test_read_files_by_extension(mock_read_files):
    """Test read_files_by_extension tool function."""
    extension = "py"
    start_dir = "src"
    read_files_by_extension(extension, start_dir)
    mock_read_files.assert_called_once_with("*.py", "src")


@patch("src.tools.filesystem_tools.Path.read_text", side_effect=mock_path_read_text)
def test_read_file(mock_read_text):
    """Test read_file tool function."""
    path = "test_dir/file1.txt"
    result = read_file(path)
    assert result == "content of file1"


@patch("src.tools.filesystem_tools.Path.write_text", side_effect=mock_path_write_text)
def test_write_file(mock_write_text):
    """Test write_file tool function."""
    path = "test_dir/new_file.txt"
    content = "new file content"
    result = write_file(path, content)
    assert result == f"Successfully wrote to {path}"
    mock_write_text.assert_called_once_with(content)


@patch("src.tools.filesystem_tools.Path.rglob", side_effect=mock_path_rglob)
@patch("src.tools.filesystem_tools.Path.cwd", return_value=Path("."))
@patch("os.walk", side_effect=mock_os_walk)
def test_find_files(mock_os_walk, mock_cwd, mock_rglob):
    """Test find_files tool function."""
    pattern = "*.py"
    start_dir = "."
    result = find_files(pattern, start_dir)
    expected = ["test_dir/subdir/file3.py"]
    assert result == expected


@patch("src.tools.filesystem_tools.Path.stat", side_effect=mock_path_stat)
@patch("src.tools.filesystem_tools.Path.is_file", side_effect=mock_path_is_file)
@patch("src.tools.filesystem_tools.Path.is_dir", side_effect=mock_path_is_dir)
@patch("src.tools.filesystem_tools.Path.cwd", return_value=Path("."))
def test_get_file_info(mock_cwd, mock_is_dir, mock_is_file, mock_stat):
    """Test get_file_info tool function."""
    path = "test_dir/file1.txt"
    result = get_file_info(path)
    expected = {"size": 100, "modified": 1678886400, "type": "file", "path": "test_dir/file1.txt"}
    assert result == expected
