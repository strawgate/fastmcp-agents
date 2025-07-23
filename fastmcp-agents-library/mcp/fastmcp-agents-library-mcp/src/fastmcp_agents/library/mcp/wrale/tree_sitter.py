from textwrap import dedent

from fastmcp.mcp_config import TransformingStdioMCPServer
from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig


def tree_sitter_mcp() -> TransformingStdioMCPServer:
    return TransformingStdioMCPServer(
        command="uvx",
        args=["mcp-server-tree-sitter"],
        env={"MCP_TS_LOG_LEVEL": "WARNING"},
        tools={
            "register_project_tool": ToolTransformConfig(
                arguments={
                    "name": ArgTransformConfig(
                        name="name",
                        description=dedent(
                            text="""The name of the project to register. All further calls that take a project name will be made using the
                            value provided in this parameter. A good name is typically the name of the project directory."""
                        ),
                    ),
                },
            )
        },
    )
