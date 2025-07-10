from fastmcp.tools.tool import Tool
from fastmcp.server.server import FastMCP
import json
from typing import Any

from fastmcp import FastMCP
from mcp.types import TextContent

from fastmcp_agents.cli.models.config import FastMCPAgentsConfig
from fastmcp_agents.cli.models.servers import StdioMCPServerConfig
from fastmcp_agents.cli.models.tools import StaticStringTool, ToolTransform

from .conftest import STDIO_FETCH_ARGS, STDIO_FETCH_COMMAND, STDIO_TIME_ARGS, STDIO_TIME_COMMAND


def test_init():
    """Test the FastMCPAgentsConfig model."""

    config = FastMCPAgentsConfig()

    assert config.name is None
    assert len(config.agents) == 0
    assert len(config.mcp) == 0
    assert len(config.tools) == 0


async def test_activate_name_and_tools():
    """Test the FastMCPAgentsConfig model with a name and tools."""

    config = FastMCPAgentsConfig(
        name="test",
        tools=[
            StaticStringTool(
                name="test tool",
                description="test tool description",
                returns="test",
            ),
        ],
    )

    root_server = FastMCP(name="root_server")

    await config.activate(fastmcp_server=root_server)

    tools = await root_server.get_tools()

    assert len(tools) == 1
    test_tool = tools["test tool"]
    assert test_tool.description == "test tool description"

    result = await test_tool.run(arguments={})

    assert result.content[0] is not None
    assert isinstance(result.content[0], TextContent)
    assert result.content[0].text == "test"


async def test_activate_mcp_server_with_overrides():
    """Test the FastMCPAgentsConfig model with a name and tools."""

    config = FastMCPAgentsConfig(
        name="best_agent_server_of_all_time",
        mcp={
            "time_server": StdioMCPServerConfig(
                command=STDIO_TIME_COMMAND,
                args=STDIO_TIME_ARGS,
                tools={
                    "get_current_time": ToolTransform(
                        name="get_some_other_time",
                        description="A way better description of the tool",
                    ),
                    "convert_time": ToolTransform(
                        enabled=False,
                    ),
                },
            ),
        },
    )

    root_server = FastMCP(name="root_server")

    await config.activate(fastmcp_server=root_server)

    tools = await root_server.get_tools()

    assert len(tools) == 1
    test_tool = tools["get_some_other_time"]
    assert test_tool.description == "A way better description of the tool"

    result = await test_tool.run(arguments={"timezone": "America/New_York"})

    assert result.content[0] is not None
    assert isinstance(result.content[0], TextContent)
    result_text = result.content[0].text

    result_as_dict = json.loads(result_text)

    assert result_as_dict["timezone"] == "America/New_York"
    assert "datetime" in result_as_dict
    assert "is_dst" in result_as_dict


async def test_activate_nested_agents():
    """Test the FastMCPAgentsConfig model with a nested MCP server."""

    config = FastMCPAgentsConfig(
        name="best_agent_server_of_all_time",
        mcp={
            "agent_server": FastMCPAgentsConfig(
                name="nested_agent_server",
                mcp={
                    "fetch_server": StdioMCPServerConfig(
                        command=STDIO_FETCH_COMMAND,
                        args=STDIO_FETCH_ARGS,
                    ),
                },
            ),
            "time_server": StdioMCPServerConfig(
                command=STDIO_TIME_COMMAND,
                args=STDIO_TIME_ARGS,
            ),
        },
    )

    root_server: FastMCP[Any] = FastMCP(name="root_server")

    _ = await config.activate(fastmcp_server=root_server)

    tools: dict[str, Tool] = await root_server.get_tools()

    assert len(tools) == 3
    assert "fetch" in tools
    assert "get_current_time" in tools
    assert "convert_time" in tools
