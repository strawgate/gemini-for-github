import pytest

from gemini_for_github.clients.filesystem import DirectoryInfo, FileInfo, FilesystemClient


@pytest.fixture
def temp_filesystem_client(tmp_path):
    """Fixture to create a temporary directory and a FilesystemClient instance."""
    # Create some dummy files and directories
    (tmp_path / "test_file.txt").write_text("hello world")
    (tmp_path / "another_file.md").write_text("# Markdown")
    (tmp_path / "test_dir").mkdir()
    (tmp_path / "test_dir" / "nested_file.py").write_text("print('hello')")

    return FilesystemClient(root=tmp_path)


def test_get_file_info_no_exception(temp_filesystem_client, tmp_path):
    """Test get_file_info does not raise exception for a valid file."""
    file_path = str(tmp_path / "test_file.txt")
    try:
        file_info = temp_filesystem_client.get_file_info(file_path)
        assert isinstance(file_info, FileInfo)
    except Exception as e:
        pytest.fail(f"get_file_info raised an exception: {e}")


def test_get_file_content_no_exception(temp_filesystem_client, tmp_path):
    """Test get_file_content does not raise exception for a valid file."""
    file_path = str(tmp_path / "test_file.txt")
    try:
        content = temp_filesystem_client.get_file_content(file_path)
        assert isinstance(content, str)
        assert content == "hello world"
    except Exception as e:
        pytest.fail(f"get_file_content raised an exception: {e}")


def test_get_files_content_no_exception(temp_filesystem_client, tmp_path):
    """Test get_files_content does not raise exception for valid files."""
    file_paths = [str(tmp_path / "test_file.txt"), str(tmp_path / "another_file.md")]
    try:
        content_dict = temp_filesystem_client.get_files_content(file_paths)
        assert isinstance(content_dict, dict)
        assert len(content_dict) == 2
        assert "hello world" in content_dict.values()
        assert "# Markdown" in content_dict.values()
    except Exception as e:
        pytest.fail(f"get_files_content raised an exception: {e}")


def test_get_directory_info_no_exception(temp_filesystem_client, tmp_path):
    """Test get_directory_info does not raise exception for a valid directory."""
    dir_path = str(tmp_path)
    try:
        dir_info = temp_filesystem_client.get_directory_info(dir_path)
        assert isinstance(dir_info, DirectoryInfo)
    except Exception as e:
        pytest.fail(f"get_directory_info raised an exception: {e}")


def test_get_directory_info_nested_no_exception(temp_filesystem_client, tmp_path):
    """Test get_directory_info with levels > 1 does not raise exception."""
    dir_path = str(tmp_path)
    try:
        dir_info = temp_filesystem_client.get_directory_info(dir_path, levels=2)
        assert isinstance(dir_info, DirectoryInfo)
    except Exception as e:
        pytest.fail(f"get_directory_info raised an exception: {e}")


def test_get_directory_info_hidden_files(temp_filesystem_client, tmp_path):
    """Test get_directory_info handles hidden files correctly."""
    # Create a hidden file
    hidden_file_path = tmp_path / ".hidden_file"
    hidden_file_path.write_text("hidden content")

    # Test with exclude_hidden=True (default)
    dir_info_excluded = temp_filesystem_client.get_directory_info(str(tmp_path), exclude_hidden=True)
    assert not any(child.name == ".hidden_file" for child in dir_info_excluded.children)

    # Test with exclude_hidden=False
    dir_info_included = temp_filesystem_client.get_directory_info(str(tmp_path), exclude_hidden=False)
    assert any(child.name == ".hidden_file" for child in dir_info_included.children)


def test_get_directory_info_hidden_folders(temp_filesystem_client, tmp_path):
    """Test get_directory_info handles hidden folders correctly."""
    # Create a hidden directory
    hidden_dir_path = tmp_path / ".hidden_dir"
    hidden_dir_path.mkdir()

    # Test with exclude_hidden=True (default)
    dir_info_excluded = temp_filesystem_client.get_directory_info(str(tmp_path), exclude_hidden=True)
    assert not any(child.name == ".hidden_dir" for child in dir_info_excluded.children)

    # Test with exclude_hidden=False
    dir_info_included = temp_filesystem_client.get_directory_info(str(tmp_path), exclude_hidden=False)
    assert any(child.name == ".hidden_dir" for child in dir_info_included.children)


def test_get_directory_info_include_globs(temp_filesystem_client, tmp_path):
    """Test get_directory_info with include_globs."""
    # Create files with different extensions
    (tmp_path / "file1.txt").write_text("content")
    (tmp_path / "file2.log").write_text("content")
    (tmp_path / "file3.txt").write_text("content")

    # Test with include_globs
    include_globs = ["*.txt"]
    dir_info = temp_filesystem_client.get_directory_info(str(tmp_path), include_globs=include_globs)
    children_names = [child.name for child in dir_info.children]
    assert "file1.txt" in children_names
    assert "file3.txt" in children_names
    assert "file2.log" not in children_names


def test_get_directory_info_exclude_globs(temp_filesystem_client, tmp_path):
    """Test get_directory_info with exclude_globs."""
    # Create files with different extensions
    (tmp_path / "file1.txt").write_text("content")
    (tmp_path / "file2.log").write_text("content")
    (tmp_path / "file3.txt").write_text("content")

    # Test with exclude_globs
    exclude_globs = ["*.log"]
    dir_info = temp_filesystem_client.get_directory_info(str(tmp_path), exclude_globs=exclude_globs)
    children_names = [child.name for child in dir_info.children]
    assert "file1.txt" in children_names
    assert "file3.txt" in children_names
    assert "file2.log" not in children_names


def test_get_directory_info_include_and_exclude_globs(temp_filesystem_client, tmp_path):
    """Test get_directory_info with both include and exclude globs."""
    # Create files with different extensions
    (tmp_path / "file1.txt").write_text("content")
    (tmp_path / "file2.log").write_text("content")
    (tmp_path / "file3.txt").write_text("content")
    (tmp_path / "file4.md").write_text("content")

    # Test with include and exclude globs
    include_globs = ["*.txt", "*.md"]
    exclude_globs = ["file3.txt"]
    dir_info = temp_filesystem_client.get_directory_info(str(tmp_path), include_globs=include_globs, exclude_globs=exclude_globs)
    children_names = [child.name for child in dir_info.children]
    assert "file1.txt" in children_names
    assert "file4.md" in children_names
    assert "file2.log" not in children_names
    assert "file3.txt" not in children_names
