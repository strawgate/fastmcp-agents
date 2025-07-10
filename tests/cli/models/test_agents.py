from typing import Any

import pytest
from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.cli.models.agents import AgentModel


def test_init():
    """Test the AgentModel model."""

    agent = AgentModel(
        name="test agent",
        description="test agent description",
        instructions="test agent instructions",
        allowed_tools=["test tool"],
        blocked_tools=["test tool 2"],
    )

    assert agent.name == "test agent"
    assert agent.description == "test agent description"
    assert agent.instructions == "test agent instructions"
    assert agent.allowed_tools == ["test tool"]
    assert agent.blocked_tools == ["test tool 2"]


@pytest.fixture
def fastmcp_server_with_tools() -> FastMCP[Any]:
    """A FastMCP server."""

    def tool_one_fn(param1: str, param2: str) -> str:  # noqa: ARG001
        """test tool one."""

        return "test tool one"

    def tool_two_fn(param1: str, param2: str) -> str:  # noqa: ARG001
        """test tool two."""

        return "test tool two"

    fastmcp_server = FastMCP()

    fastmcp_server.add_tool(
        FunctionTool.from_function(
            tool_one_fn,
            name="tool_one",
            description="test tool one",
        )
    )
    fastmcp_server.add_tool(
        FunctionTool.from_function(
            tool_two_fn,
            name="tool_two",
            description="test tool two",
        )
    )

    return fastmcp_server


async def test_activate(fastmcp_server_with_tools: FastMCP[Any]):
    """Test the activate method."""

    agent = AgentModel(
        name="ask_test_agent",
        description="test agent description",
        instructions="test agent instructions",
        allowed_tools=["tool_one"],
        blocked_tools=["tool_two"],
    )

    activated_agent = await agent.activate(fastmcp_server=fastmcp_server_with_tools)

    assert isinstance(activated_agent, CuratorAgent)
    assert activated_agent.name == "ask_test_agent"
    assert activated_agent.description == "test agent description"
    assert activated_agent.instructions == "test agent instructions"
    assert activated_agent.system_prompt == "test agent instructions"
    assert len(activated_agent.default_tools) == 1
    assert activated_agent.default_tools[0].name == "tool_one"
    assert activated_agent.default_tools[0].description == "test tool one"

    tools = await fastmcp_server_with_tools.get_tools()

    assert len(tools) == 3

    assert "ask_test_agent" in tools
    assert "tool_one" in tools
    assert "tool_two" in tools
