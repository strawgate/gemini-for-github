"""
MCP Server for performing file operations.

This server provides tools for reading, creating, appending, erasing, moving,
and deleting files, with centralized exception handling.
"""

import os
import shutil
from collections.abc import Callable
from contextlib import asynccontextmanager
from fnmatch import fnmatch
from pathlib import Path

from fastmcp.contrib.mcp_mixin import MCPMixin
from pydantic import BaseModel, Field

from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("filesystem")

DEFAULT_SKIP_LIST = [
    "**/.?*/**",
    ".?*/**",  # exclude hidden folders
    "**/.?*",  # exclude hidden files
    "**/.git/**",
    ".git/*",
    "**/.svn/**",
    ".svn/*",
    "**/.mypy_cache/**",
    ".mypy_cache/*",
    "**/.pytest_cache/**",
    "*.pytest_cache/*",
    "**/__pycache__/**",
    "*__pycache__/*",
    "**/.venv/**",
    ".venv/*",
]

DEFAULT_SKIP_READ = [
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.hg",
    "*.tox",
    "*.com",
    "*.class",
    "*.dll",
    "*.exe",
    "*.o",
    "*.so",
    "*.7z",
    "*.dmg",
    "*.gz",
    "*.iso",
    "*.jar",
    "*.rar",
    "*.tar",
    "*.zip",
    "*.msi",
    "*.sqlite",
    "*.DS_Store",
    "*.DS_Store?",
    "*._*",
    "*.Spotlight-V100",
    "*.Trashes",
    "*ehthumbs.db",
    "*Thumbs.db",
    "*desktop.ini",
    "*.bak",
    "*.swp",
    "*.swo",
    "*~",
    "*#",
]


class MCPFileSystemOperationError(Exception):
    """Base exception for bulk filesystem operations."""


class MCPFileOperationError(MCPFileSystemOperationError):
    """Exception raised for errors during file operations."""

    def __init__(self, message, file_path):
        self.file_path = file_path
        super().__init__(f"Error performing operation on file {file_path}: {message}")


class MCPFolderOperationError(MCPFileSystemOperationError):
    """Exception raised for errors during folder operations."""

    def __init__(self, message, folder_path):
        self.folder_path = folder_path
        super().__init__(f"Error performing operation on folder {folder_path}: {message}")


class MCPFileNotFoundError(MCPFileOperationError):
    """Exception raised when a file is not found."""

    def __init__(self, file_path):
        super().__init__("File not found", file_path)


class MCPFolderNotFoundError(MCPFolderOperationError):
    """Exception raised when a folder is not found."""

    def __init__(self, folder_path):
        super().__init__("Folder not found", folder_path)


@asynccontextmanager
async def handle_file_errors(path: str):
    """
    Async context manager to handle file operation exceptions.
    """
    try:
        logger.info(f"Handling file operation for {path}")
        yield
        logger.info(f"File operation completed successfully for {path}")
    except FileNotFoundError as e:
        msg = f"File not found: {e}"
        logger.exception(msg)
        raise MCPFileNotFoundError(path) from e
    except PermissionError as e:
        msg = f"Permission denied: {e}"
        logger.exception(msg)
        raise MCPFileOperationError(msg, path) from e
    except Exception as e:
        msg = f"An unexpected error occurred: {e}"
        logger.exception(msg)
        raise MCPFileOperationError(msg, path) from e


@asynccontextmanager
async def handle_folder_errors(path: str):
    """
    Async context manager to handle folder operation exceptions.
    """
    try:
        logger.info(f"Handling folder operation for {path}")
        yield
        logger.info(f"Folder operation completed successfully for {path}")
    except FileNotFoundError as e:
        msg = f"File not found: {e}"
        logger.exception(msg)
        raise MCPFolderNotFoundError(path) from e
    except PermissionError as e:
        msg = f"Permission denied: {e}"
        logger.exception(msg)
        raise MCPFolderOperationError(msg, path) from e
    except Exception as e:
        msg = f"An unexpected error occurred: {e}"
        logger.exception(msg)
        raise MCPFolderOperationError(msg, path) from e


class FileOperations:
    """
    This class provides tools to manipulate files.

    It includes methods for reading, creating, appending, erasing, moving,
    and deleting files, with integrated custom exception handling.
    """

    def __init__(self, root_dir: Path):
        """
        Initializes the FileOperations class.
        Args:
            root_dir: The root directory to perform file operations on.
        """
        self.root_dir = root_dir

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the file operations."""
        return {
            "file_read": self.read,
            "file_create": self.create,
            "file_append": self.append,
            "file_erase": self.erase,
            "file_move": self.move,
            "file_delete": self.delete,
        }

    async def read(self, file_path: str) -> str:
        """
        Reads the content of a file at the specified path.

        Args:
            file_path: The path of the file to read.

        Returns:
            str: The content of the file.
        """
        async with handle_file_errors(file_path):
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        logger.info(f"File read successfully from {file_path}: {content[:100]}")
        return content

    async def create(self, file_path: str, content: str) -> bool:
        """
        Creates a file with the specified content.

        Args:
            file_path: The path where the file should be created.
            content: The content to write into the file.

        Returns:
            bool: True if the file was created successfully, False otherwise.
        """
        async with handle_file_errors(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"File created successfully at {file_path}")
            return True

    async def append(self, file_path: str, content: str) -> bool:
        """
        Appends content to an existing file.

        Args:
            file_path: The path of the file to append content to.
            content: The content to append to the file.

        Returns:
            bool: True if the content was appended successfully, False otherwise.
        """
        async with handle_file_errors(file_path):
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Content appended successfully to {file_path}")
            return True

    async def erase(self, file_path: str) -> bool:
        """
        Erases the content of a file.

        Args:
            file_path: The path of the file to erase.

        Returns:
            bool: True if the file was erased successfully, False otherwise.
        """
        async with handle_file_errors(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("")
            logger.info(f"File content erased successfully at {file_path}")
            return True

    async def move(self, source_path: str, destination_path: str) -> bool:
        """
        Moves a file from source to destination.

        Args:
            source_path: The current path of the file.
            destination_path: The new path where the file should be moved.

        Returns:
            bool: True if the file was moved successfully, False otherwise.
        """
        async with handle_file_errors(source_path):
            os.rename(source_path, destination_path)
            logger.info(f"File moved from {source_path} to {destination_path}")
            return True

    async def delete(self, file_path: str) -> bool:
        """
        Deletes a file at the specified path.

        Args:
            file_path: The path of the file to delete.

        Returns:
            bool: True if the file was deleted successfully, False otherwise.
        """
        async with handle_file_errors(file_path):
            os.remove(file_path)
            logger.info(f"File deleted successfully at {file_path}")
            return True


class BaseMultiFileReadResult(BaseModel):
    file_path: str


class FileReadError(BaseMultiFileReadResult):
    """
    A model to represent an error that occurred while reading a file.

    Attributes:
        file_path (str): The path of the file that caused the error.
        error (str): The error message.
    """

    error: str


class FileReadSuccess(BaseModel):
    """
    A model to represent a successful file read operation.

    Attributes:
        file_path (str): The path of the file that was read.
        content (str): The content of the file.
    """

    file_path: str
    content: str


class FileReadSummary(BaseModel):
    """
    A model to summarize the results of reading files.

    Attributes:
        total_files (int): The total number of files read.
        successful_reads (int): The number of files read successfully.
        errors (list[FileReadError]): A list of errors encountered while reading files.
    """

    total_files: int = Field(default=0, description="Total number of files processed")
    skipped_files: int = Field(default=0, description="Number of files skipped due to exclusions")
    errors: list[FileReadError] = Field(default_factory=list, description="List of errors encountered while reading files")
    results: list[FileReadSuccess] = Field(default_factory=list, description="List of successfully read files with their content")


class FolderOperations(MCPMixin):
    """
    This class provides MCP tools to manipulate folders.

    It includes methods for creating, listing contents, moving, deleting,
    and emptying folders, with integrated custom exception handling.
    """

    read_file_exclusions: list[str] = Field(
        default_factory=list, description="List of file patterns to exclude from all multi-read operations."
    )
    list_folder_exclusions: list[str] = Field(
        default_factory=list, description="List of folder patterns to exclude from listing operations."
    )

    def __init__(self, root_dir: Path):
        """
        Initializes the FolderOperations class.
        Args:
            denied_operations: A list of operations that should be denied.
        """
        self.read_file_exclusions = DEFAULT_SKIP_READ
        self.list_folder_exclusions = DEFAULT_SKIP_LIST
        self.root_dir = root_dir
        super().__init__()

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the folder operations."""
        return {
            "folder_contents": self.contents,
            "folder_read_all": self.read_all,
            "folder_move": self.move,
            "folder_delete": self.delete,
        }

    async def create(self, folder_path: str) -> bool:
        """
        Creates a folder at the specified path.

        Args:
            folder_path: The path where the folder should be created.

        Returns:
            bool: True if the folder was created successfully, False otherwise.
        """
        async with handle_folder_errors(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            logger.info(f"Folder created successfully at {folder_path}")
            return True

    def _matches_globs(self, path: str, include: list[str], exclude: list[str]) -> bool:
        """
        Checks if the given path matches the include and exclude glob patterns.

        Args:
            path: The path to check.
            include: A list of glob patterns to include specific files.
            exclude: A list of glob patterns to exclude specific files.

        Returns:
            bool: True if the path matches the include patterns and does not match the exclude patterns.
        """

        if include:
            included = any(fnmatch(path, pat) for pat in include)
        else:
            included = True

        excluded = any(fnmatch(path, pat) for pat in exclude)

        return included and not excluded

    async def contents(
        self, folder_path: str, include: list[str], exclude: list[str], recurse: bool, bypass_default_exclusions: bool = False
    ) -> list:
        """
        Lists the contents of a folder.
         If you are listing items recursively, the include and exclude patterns will
         apply to the relative path of the items. So to capture all files of a certain type
         in a folder and its subfolders, you would use a pattern like `**/*.txt` for `include`.

        Args:
            folder_path: The path of the folder to list.
            include: A list of glob patterns to include specific files, applies to the relative path.
            exclude: A list of glob pattern to exclude specific files, applies to the relative path.
            recurse: If True, lists contents recursively.

        Returns:
            list: A list of items in the folder.
        """
        async with handle_folder_errors(folder_path):
            contents = []

            if recurse:
                for dir_, _, files in os.walk(folder_path):
                    for file_name in files:
                        rel_dir = os.path.relpath(dir_, folder_path)
                        rel_file = os.path.join(rel_dir, file_name)

                        if not bypass_default_exclusions:
                            # Check if the file matches any default exclusion patterns
                            if not self._matches_globs(rel_file, include=["*"], exclude=self.list_folder_exclusions):
                                logger.debug(f"Skipping file due to folder exclusions: {rel_file}")
                                continue

                        if self._matches_globs(rel_file, include, exclude):
                            contents.append(rel_file)
                            logger.debug(f"Included file: {rel_file}")
            else:
                contents = os.listdir(folder_path)

            logger.info(f"Contents of {folder_path} listed successfully {len(contents)} files")
            return contents

    async def read_all(
        self,
        folder_path: str,
        include: list[str],
        exclude: list[str],
        recurse: bool,
        head: int = 0,
        tail: int = 0,
        bypass_default_exclusions: bool = False,
    ) -> FileReadSummary:
        """
        Provides the full contents (every character) of every file in a folder.
         If you are listing items recursively, the include and exclude patterns will
         apply to the relative path of the items. So to capture all files of a certain type
         in a folder and its subfolders, you would use a pattern like `**/*.txt` for `include`.

        Args:
            folder_path: The path of the folder to list.
            include: A glob pattern to include specific files, applies to the relative path.
            exclude: A glob pattern to exclude specific files, applies to the relative path.
            recurse: If True, reads files recursively.
            head: Number of lines to read from the start of each file (default is 0, meaning read all).
            tail: Number of lines to read from the end of each file (default is 0, meaning read all).
            bypass_default_exclusions: If True, skips the default exclusions for reading files.

        Returns:
            list[FileReadSuccess | FileReadError]: A list of results containing the file path and content or error.
        """
        async with handle_folder_errors(folder_path):
            files = await self.contents(folder_path, include, exclude, recurse, bypass_default_exclusions)
            unfiltered_file_count = len(await self.contents(folder_path, [], [], recurse, bypass_default_exclusions))

            results: list[FileReadSuccess] = []
            errors: list[FileReadError] = []

            for file in files:
                file_path = os.path.join(folder_path, file)

                if not bypass_default_exclusions:
                    # Check if the file matches any default exclusion patterns
                    if not self._matches_globs(file, include=["*"], exclude=self.read_file_exclusions):
                        logger.debug(f"Skipping file due to exclusion: {file_path}")
                        continue

                if not os.path.isfile(file_path):
                    continue
                try:
                    with open(file_path, encoding="utf-8", errors="strict") as f:
                        if head > 0:
                            content = "".join(f.readlines()[:head])
                        elif tail > 0:
                            f.seek(0, os.SEEK_END)
                            f.seek(max(0, f.tell() - tail), os.SEEK_SET)
                            content = f.read()
                        else:
                            content = f.read()
                    results.append(FileReadSuccess(file_path=file, content=content))
                    logger.debug(f"File read successfully: {file_path}")
                except Exception as e:
                    errors.append(FileReadError(file_path=file, error=str(e)))
                    logger.error(f"Error reading file {file_path}: {e}")

            summary = FileReadSummary(
                total_files=len(files),
                skipped_files=unfiltered_file_count - len(files),
                errors=errors,
                results=results,
            )
            logger.info(f"File read summary: {summary}")
            return summary

    async def move(self, source_path: str, destination_path: str) -> bool:
        """
        Moves a folder from source to destination.

        Args:
            source_path: The current path of the folder.
            destination_path: The new path where the folder should be moved.

        Returns:
            bool: True if the folder was moved successfully, False otherwise.
        """
        async with handle_folder_errors(source_path):
            os.rename(source_path, destination_path)
            logger.info(f"Folder moved from {source_path} to {destination_path}")
            return True

    async def delete(self, folder_path: str, recursive: bool = False) -> bool:
        """
        Deletes a folder at the specified path.

        Args:
            folder_path: The path of the folder to delete.
            recursive: If True, deletes the folder and all its contents recursively.

        Returns:
            bool: True if the folder was deleted successfully, False otherwise.
        """
        async with handle_folder_errors(folder_path):
            if recursive:
                shutil.rmtree(folder_path)
            else:
                os.rmdir(folder_path)
            logger.info(f"Folder deleted successfully at {folder_path}")
            return True
