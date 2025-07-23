from collections.abc import Generator
from pathlib import Path

from fastmcp.mcp_config import TransformingStdioMCPServer
from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig
from pydantic import BaseModel, Field, computed_field


def read_write_filesystem_mcp(root_dir: Path | None = None) -> TransformingStdioMCPServer:
    additional_args: list[str] = []
    if root_dir is not None:
        additional_args.append(f"--root-dir={root_dir.resolve()}")

    return TransformingStdioMCPServer(
        command="uvx",
        args=["filesystem-operations-mcp", *additional_args],
        tools={
            "search_files": ToolTransformConfig(
                arguments={
                    "included_types": ArgTransformConfig(hide=True),
                    "excluded_types": ArgTransformConfig(hide=True),
                },
            ),
            "find_files": ToolTransformConfig(
                arguments={
                    "included_types": ArgTransformConfig(hide=True),
                    "excluded_types": ArgTransformConfig(hide=True),
                },
            ),
        },
    )


def read_only_filesystem_mcp(root_dir: Path | None = None) -> TransformingStdioMCPServer:
    mcp = read_write_filesystem_mcp(root_dir=root_dir)

    mcp.tools = {
        "find_files": ToolTransformConfig(
            tags={"allowed_tools"},
            arguments={
                "included_types": ArgTransformConfig(hide=True),
                "excluded_types": ArgTransformConfig(hide=True),
            },
        ),
        "search_files": ToolTransformConfig(
            tags={"allowed_tools"},
            arguments={
                "included_types": ArgTransformConfig(hide=True),
                "excluded_types": ArgTransformConfig(hide=True),
            },
        ),
        "get_structure": ToolTransformConfig(
            tags={"allowed_tools"},
        ),
        "get_file": ToolTransformConfig(
            tags={"allowed_tools"},
        ),
        "read_file_lines": ToolTransformConfig(
            tags={"allowed_tools"},
        ),
    }

    mcp.include_tags = {"allowed_tools"}

    return mcp


class FileStructure(BaseModel):
    """A file structure."""

    results: list[str]
    max_results: int = Field(description="The maximum number of results to return.", exclude=True)

    @computed_field
    @property
    def limit_reached(self) -> bool:
        """Check if the limit has been reached."""

        return len(self.results) >= self.max_results


def get_structure(root_dir: Path, max_results: int = 150) -> FileStructure:
    """Get the structure of a directory."""

    results: list[str] = []

    for item in limited_depth_iterdir(path=root_dir, max_depth=3):
        if len(results) >= max_results:
            break
        if item.is_file():
            results.append(item.name)
        elif item.is_dir():
            results.append(item.name + "/")

    return FileStructure(results=results, max_results=max_results)


def limited_depth_iterdir(
    path: Path,
    max_depth: int = 3,
    current_depth: int = 0,
) -> Generator[Path]:
    """
    Iterates through directory contents up to a specified maximum depth.

    Args:
        path (Path): The starting directory path.
        max_depth (int): The maximum depth to traverse (0 for current directory only).
        current_depth (int): The current depth during recursion (internal use).

    Yields:
        Path: A path object for each file or directory within the depth limit.
    """
    if current_depth > max_depth:
        return

    for item in path.iterdir():
        yield item
        if item.is_dir():
            yield from limited_depth_iterdir(path=item, max_depth=max_depth, current_depth=current_depth + 1)
