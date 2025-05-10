from fnmatch import fnmatch
from pathlib import Path
from typing import Callable, Union

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
        path: str,
        levels: int = 1,
        exclude_hidden: bool = True,
        exclude_globs: Union[list[str], None] = None,  # noqa: UP007
        include_globs: Union[list[str], None] = None,  # noqa: UP007
    ) -> DirectoryInfo:
        p = Path(path)
        if not p.is_dir():
            msg = f"Directory {path} is not a directory"
            raise FilesystemNotFoundError(msg)

        children = [child for child in p.iterdir() if not child.name.startswith(".")] if exclude_hidden else list(p.iterdir())

        if exclude_globs:
            children = [child for child in children if not any(fnmatch(child.name, glob) for glob in exclude_globs)]

        if include_globs:
            children = [child for child in children if any(fnmatch(child.name, glob) for glob in include_globs)]

        children_count = len(list(p.iterdir()))

        if levels == 0:
            return DirectoryInfo(path=str(p.relative_to(Path.cwd())), children=[], children_count=children_count)

        children = [
            self.get_file_info(str(child)) if child.is_file() else self.get_directory_info(str(child), levels - 1) for child in p.iterdir()
        ]

        return DirectoryInfo(path=str(p.relative_to(Path.cwd())), children=children, children_count=children_count)
