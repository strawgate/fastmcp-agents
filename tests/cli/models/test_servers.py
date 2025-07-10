from typing import Any
import pytest
from fastmcp import FastMCP

from fastmcp_agents.cli.models.servers import StdioMCPServerConfig
from fastmcp_agents.cli.models.tools import ToolTransform

STDIO_TIME_COMMAND = "uvx"
STDIO_TIME_ARGS = ["mcp-server-time", "--local-timezone=America/New_York"]


@pytest.fixture
def fastmcp_server() -> FastMCP[Any]:
    """A fixture for a FastMCP server."""
    return FastMCP(name="test")


class TestStdio:
    def test_init(self) -> None:
        """Test the StdioMCPServerConfig model."""

        config = StdioMCPServerConfig(command=STDIO_TIME_COMMAND, args=STDIO_TIME_ARGS)

        stdio_transport = config.to_transport()

        assert stdio_transport.command == STDIO_TIME_COMMAND
        assert stdio_transport.args == STDIO_TIME_ARGS

    async def test_startup(self, fastmcp_server: FastMCP[Any]) -> None:
        """Test the StdioMCPServerConfig model."""

        config = StdioMCPServerConfig(command=STDIO_TIME_COMMAND, args=STDIO_TIME_ARGS)

        _ = await config.activate(fastmcp_server=fastmcp_server)

        tools = await fastmcp_server.get_tools()

        assert len(tools) == 2

    async def test_tool_wrapping(self, fastmcp_server: FastMCP[Any]) -> None:
        """Test the StdioMCPServerConfig model."""

        tool_transformations: dict[str, ToolTransform] = {
            "get_current_time": ToolTransform(
                name="get_some_other_time",
                enabled=False,
            ),
            "convert_time": ToolTransform(name="convert_time", description="A way better description of the tool"),
        }

        config = StdioMCPServerConfig(command=STDIO_TIME_COMMAND, args=STDIO_TIME_ARGS, tools=tool_transformations)

        _ = await config.activate(fastmcp_server=fastmcp_server)

        tools = await fastmcp_server.get_tools()

        assert len(tools) == 1

        assert tools["convert_time"].description == "A way better description of the tool"
