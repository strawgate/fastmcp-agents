from pathlib import Path

from fastmcp.mcp_config import TransformingStdioMCPServer
from fastmcp.tools.tool_transform import ToolTransformConfig


def read_write_filesystem_mcp(root_dir: Path | None = None) -> TransformingStdioMCPServer:
    """Create a read/write Filesystem MCP server.

    If root_dir is provided, the filesystem operations will be limited to the root directory.
    If root_dir is not provided, the filesystem operations will be limited to the current working directory."""

    additional_args: list[str] = []
    if root_dir is not None:
        _ = additional_args.append(f"--root-dir={root_dir}")

    return TransformingStdioMCPServer(
        command="uvx",
        args=["filesystem-operations-mcp", *additional_args],
        tools={},
    )


def read_only_filesystem_mcp(root_dir: Path | None = None) -> TransformingStdioMCPServer:
    """Create a read-only Filesystem MCP server.

    If root_dir is provided, the filesystem operations will be limited to the root directory.
    If root_dir is not provided, the filesystem operations will be limited to the current working directory."""

    mcp: TransformingStdioMCPServer = read_write_filesystem_mcp(root_dir=root_dir)

    allowlist_transform_tags = {"allowed_tools"}

    allowlist_transform_config = ToolTransformConfig(
        tags=allowlist_transform_tags,
    )

    mcp.tools["search_files"] = allowlist_transform_config
    mcp.tools["find_files"] = allowlist_transform_config
    mcp.tools["get_structure"] = allowlist_transform_config
    mcp.tools["get_file"] = allowlist_transform_config
    mcp.tools["read_file_lines"] = allowlist_transform_config

    mcp.include_tags = allowlist_transform_tags

    return mcp
