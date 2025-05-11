from collections.abc import Callable
from fnmatch import fnmatch
from pathlib import Path
from typing import Union

from pydantic import BaseModel

from gemini_for_github.errors.filesystem import FilesystemNotFoundError, FilesystemOutsideRootError, FilesystemReadError
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("filesystem")


class DirectoryInfo(BaseModel):
    path: str
    children: list["FileInfo | DirectoryInfo"]
    children_count: int


class FileInfo(BaseModel):
    name: str
    extension: str
    relative_path: str
    size: int
    modified: float


class FilesystemClient:
    root: str

    def __init__(self, root: Path):
        self.root = str(root)

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the Filesystem client."""
        return {
            "get_file_info": self.get_file_info,
            "get_file_content": self.get_file_content,
            "get_directory_info": self.get_directory_info,
        }

    def get_file_info(self, path: str) -> FileInfo:
        logger.info(f"Getting file info for {path}")
        p = Path(path)

        if not p.is_file():
            msg = f"File {path} is not a file"
            raise FilesystemNotFoundError(msg)

        if not p.is_relative_to(self.root):
            msg = f"File {path} is not a child of the root directory"
            raise FilesystemOutsideRootError(msg)

        relative_path = str(p.relative_to(self.root))

        return FileInfo(
            name=p.name,
            extension=p.suffix,
            relative_path=relative_path,
            size=p.stat().st_size,
            modified=p.stat().st_mtime,
        )

    def get_file_content(self, path: str) -> str:
        logger.info(f"Getting file content for {path}")
        try:
            p = Path(path)
            return p.read_text()
        except Exception as e:
            msg = f"Failed to read file {path}"
            raise FilesystemReadError(msg) from e

    def get_files_content(self, paths: list[str]) -> dict[str, str]:
        return {path: self.get_file_content(path) for path in paths}

    def get_directory_info(
        self,
        relative_path: str,
        levels: int = 1,
        exclude_hidden: bool = True,
        exclude_globs: Union[list[str], None] = None,  # noqa: UP007
        include_globs: Union[list[str], None] = None,  # noqa: UP007
    ) -> DirectoryInfo:
        """Get the directory info for a given relative path.

        Args:
            relative_path: The relative path to the directory to get the info for.
            levels: The number of levels to include in the directory info.
            exclude_hidden: Whether to exclude hidden files. You must disable this to see gitignore and other hidden files.
            exclude_globs: A list of globs to exclude from the directory info.
            include_globs: A list of globs to include in the directory info.

        Returns:
            The directory info for the given relative path.
        """
        logger.info(
            f"Getting directory info for {relative_path} with levels {levels}, exclude_hidden {exclude_hidden}, exclude_globs {exclude_globs}, include_globs {include_globs}"
        )
        p = Path(relative_path)
        if not p.is_dir():
            msg = f"Directory {relative_path} is not a directory"
            raise FilesystemNotFoundError(msg)

        if not p.is_relative_to(self.root):
            msg = f"Directory {relative_path} is not a child of the root directory"
            raise FilesystemOutsideRootError(msg)

        children = [child for child in p.iterdir() if not child.name.startswith(".")] if exclude_hidden else list(p.iterdir())

        if exclude_globs:
            children = [child for child in children if not any(fnmatch(child.name, glob) for glob in exclude_globs)]

        if include_globs:
            children = [child for child in children if any(fnmatch(child.name, glob) for glob in include_globs)]

        children_count = len(list(p.iterdir()))

        if levels == 0:
            return DirectoryInfo(path=str(p.relative_to(self.root)), children=[], children_count=children_count)

        children = [
            self.get_file_info(str(child)) if child.is_file() else self.get_directory_info(str(child), levels - 1) for child in p.iterdir()
        ]

        return DirectoryInfo(path=str(p.relative_to(self.root)), children=children, children_count=children_count)
