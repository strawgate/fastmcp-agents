from fastmcp.mcp_config import TransformingStdioMCPServer
from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig


def read_write_filesystem_mcp() -> TransformingStdioMCPServer:
    return TransformingStdioMCPServer(
        command="uvx",
        args=["filesystem-operations-mcp"],
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


def read_only_filesystem_mcp() -> TransformingStdioMCPServer:
    mcp = read_write_filesystem_mcp()

    mcp.tools = {
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
