from collections.abc import Callable
from contextlib import contextmanager
from fnmatch import fnmatch
from pathlib import Path
from typing import Union

from pydantic import BaseModel

from gemini_for_github.errors.filesystem import FilesystemError, FilesystemNotFoundError, FilesystemOutsideRootError, FilesystemReadError
from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("filesystem")


class DirectoryInfo(BaseModel):
    name: str
    relative_path: str
    children: list["FileInfo | DirectoryInfo"]
    children_count: int


class FileInfo(BaseModel):
    name: str
    extension: str
    relative_path: str
    size: int
    modified: float


class FilesystemClient:
    root: Path

    def __init__(self, root: Path):
        self.root = root

    def get_tools(self) -> dict[str, Callable]:
        """Get the tools available to the Filesystem client."""
        return {
            "get_file_info": self.get_file_info,
            "get_file_content": self.get_file_content,
            "get_directory_info": self.get_directory_info,
        }

    @contextmanager
    def error_handler(self, path: str, msg: str):
        try:
            yield Path(path)
        except FilesystemError as e:
            raise e
        except Exception as e:
            logger.exception(f"Unknown error occurred while getting file info for {path}")
            raise FilesystemError(msg) from e

    def _get_rendered_path(self, root_dir: Path, relative_path: Path) -> Path:

        rendered_path = Path(root_dir).joinpath(relative_path).resolve()

        if not rendered_path.relative_to(root_dir.resolve()):
            msg = f"File {relative_path} is not a child of the root directory"
            raise FilesystemOutsideRootError(msg)

        return rendered_path

    def get_file_info(self, relative_path: str) -> FileInfo:
        logger.info(f"Getting file info for {relative_path}")

        with self.error_handler(relative_path, "Failed to get file info") as p:
            if not p.is_file():
                msg = f"File {relative_path} is not a file"
                raise FilesystemNotFoundError(msg)

            rendered_path = self._get_rendered_path(self.root, p)
            rendered_relative_path = rendered_path.relative_to(self.root)
            size = p.stat().st_size
            modified = p.stat().st_mtime

        return FileInfo(
            name=p.name,
            extension=p.suffix,
            relative_path=str(rendered_relative_path),
            size=size,
            modified=modified,
        )

    def get_file_content(self, relative_path: str) -> str:
        logger.info(f"Getting file content for {relative_path}")
        
        with self.error_handler(relative_path, "Failed to get file content") as p:
            try:
                rendered_path = self._get_rendered_path(self.root, p)
                return rendered_path.read_text()
            except Exception as e:
                msg = f"Failed to read file {relative_path}"
                raise FilesystemReadError(msg) from e

    def get_files_content(self, relative_paths: list[str]) -> dict[str, str]:
        return {relative_path: self.get_file_content(relative_path) for relative_path in relative_paths}

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

        with self.error_handler(relative_path, "Failed to get directory info") as p:

            rendered_path = self._get_rendered_path(self.root, p)
            rendered_relative_path = rendered_path.relative_to(self.root)

            if not rendered_path.is_dir():
                msg = f"Directory {relative_path} is not a directory"
                raise FilesystemNotFoundError(msg)

            children = [child for child in rendered_path.iterdir() if not child.name.startswith(".")] if exclude_hidden else list(rendered_path.iterdir())

            if exclude_globs:
                children = [child for child in children if not any(fnmatch(child.name, glob) for glob in exclude_globs)]

            if include_globs:
                children = [child for child in children if any(fnmatch(child.name, glob) for glob in include_globs)]

            children_count = len(children)

            if levels == 0:
                return DirectoryInfo(name=rendered_relative_path.name, relative_path=str(rendered_relative_path), children=[], children_count=children_count)

            children = [
                self.get_file_info(str(child)) if child.is_file() else self.get_directory_info(str(child), levels - 1) for child in children
            ]

            logger.info(f"Directory {relative_path} has {children_count} children")

        return DirectoryInfo(name=rendered_relative_path.name, relative_path=str(rendered_relative_path), children=children, children_count=children_count)
