from collections.abc import Sequence
from typing import Any

import pytest
from fastmcp import FastMCP
from fastmcp.tools import Tool as FastMCPTool
from fastmcp.client.client import Client

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.cli.models.config import FastMCPAgentsConfig
from fastmcp_agents.vendored.fastmcp_transports.patch import apply_patches


@pytest.fixture(autouse=True)
def apply_patches_fixture():
    """Apply the patches to the FastMCP server."""
    apply_patches()

@pytest.fixture
def bundled_server_name():
    """Override this fixture in test files to specify which config to use."""
    msg = "Override this fixture in test files to specify which config to use."
    raise NotImplementedError(msg)


@pytest.fixture
def bundled_server_config(bundled_server_name: str) -> FastMCPAgentsConfig:
    """Take the bundled server name (which is overridden in test files) and return the corresponding config."""
    return FastMCPAgentsConfig.from_bundled(bundled_server_name)


@pytest.fixture
async def bundled_server_activation(
    bundled_server_config: FastMCPAgentsConfig,
) -> tuple[FastMCP[Any], Sequence[CuratorAgent], Sequence[FastMCPTool], Sequence[FastMCP[Any]], Sequence[FastMCP[Any]], Sequence[Client[Any]]]:
    """Activate the bundled server config and return the FastMCP server, agents, tools, nested servers, and MCP servers."""
    return await bundled_server_config.activate(fastmcp_server=FastMCP())


@pytest.fixture
def bundled_server(
    bundled_server_activation: tuple[
        FastMCP[Any],
        Sequence[CuratorAgent],
        Sequence[FastMCPTool],
        Sequence[FastMCP[Any]],
        Sequence[FastMCP[Any]],
    ],
) -> FastMCP[Any]:
    """Get the FastMCP server instance from the bundled server activation."""
    return bundled_server_activation[0]


@pytest.fixture
def agents(
    bundled_server_activation: tuple[
        FastMCP[Any],
        Sequence[CuratorAgent],
        Sequence[FastMCPTool],
        Sequence[FastMCP[Any]],
        Sequence[FastMCP[Any]],
    ],
) -> Sequence[CuratorAgent]:
    """Get the list of FastMCP agents from the bundled server activation."""
    return bundled_server_activation[1]


@pytest.fixture
def tools(
    bundled_server_activation: tuple[
        FastMCP[Any],
        Sequence[CuratorAgent],
        Sequence[FastMCPTool],
        Sequence[FastMCP[Any]],
        Sequence[FastMCP[Any]],
    ],
) -> Sequence[FastMCPTool]:
    """Get the list of FastMCP tools from the bundled server activation."""
    return bundled_server_activation[2]


@pytest.fixture
def nested_servers(
    bundled_server_activation: tuple[
        FastMCP[Any],
        Sequence[CuratorAgent],
        Sequence[FastMCPTool],
        Sequence[FastMCP[Any]],
        Sequence[FastMCP[Any]],
    ],
) -> Sequence[FastMCP[Any]]:
    """Get the list of nested FastMCP servers from the bundled server activation."""
    return bundled_server_activation[3]


@pytest.fixture
def mcp_servers(
    bundled_server_activation: tuple[
        FastMCP[Any], Sequence[CuratorAgent], Sequence[FastMCPTool], Sequence[FastMCP[Any]], Sequence[FastMCP[Any]]
    ],
) -> Sequence[FastMCP[Any]]:
    """Get the list of MCP servers from the bundled server activation."""
    return bundled_server_activation[4]


@pytest.fixture
def agent_name():
    """Override this fixture in test files to specify the name of the agent you are testing."""
    msg = "Override this fixture in test files to specify the name of the agent you are testing."
    raise NotImplementedError(msg)


@pytest.fixture
def agent(agent_name: str, agents: Sequence[CuratorAgent]) -> CuratorAgent:
    """Get the agent instance for the agent name from the bundled server activation."""
    return next(agent for agent in agents if agent.name == agent_name)


# @pytest.fixture
# def fastmcp_server(compiled_configuration: tuple[Sequence[MultiStepAgent], list[Client], FastMCP]) -> FastMCP:
#     """Get the FastMCP server instance."""
#     return compiled_configuration[2]


# @pytest.fixture
# def mcp_clients(compiled_configuration: tuple[Sequence[MultiStepAgent], list[Client], FastMCP]) -> list[Client]:
#     """Get the list of MCP clients."""
#     return compiled_configuration[1]


# @pytest.fixture
# def agents(compiled_configuration: tuple[Sequence[MultiStepAgent], list[Client], FastMCP]) -> Sequence[MultiStepAgent]:
#     """Get the list of FastMCP agents."""
#     return compiled_configuration[0]


# @pytest.fixture
# def agent_name():
#     msg = "Override this fixture in test files to specify the name of the agent you are testing."
#     raise NotImplementedError(msg)


# @pytest.fixture
# def agent(agent_name: str, agents: Sequence[MultiStepAgent]) -> MultiStepAgent:
#     return next(agent for agent in agents if agent.name == agent_name)
