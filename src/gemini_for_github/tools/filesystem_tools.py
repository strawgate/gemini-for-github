from pathlib import Path
from typing import Any

# write_file function removed as its functionality is covered by MCP server's file_create or similar.


def get_file_info(path: str) -> dict[str, Any]:
    """Get information about a file.

    Args:
        path: Path to file, relative to git root

    Returns:
        Dictionary containing file info:
        {
            "size": int,
            "modified": str,
            "type": str,
            "path": str
        }
    """
    try:
        p = Path(path)
        return {
            "size": p.stat().st_size,
            "modified": p.stat().st_mtime,
            "type": "file" if p.is_file() else "directory",
            "path": str(p.relative_to(Path.cwd())),
        }
    except Exception as e:
        return {"error": str(e)}
