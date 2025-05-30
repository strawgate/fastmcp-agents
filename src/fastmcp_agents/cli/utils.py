from __future__ import annotations

import logging
import os
from pathlib import Path

import requests
import yaml
from fastmcp import Client, FastMCP

from fastmcp_agents.cli.models import (
    AgentConfig,
    ContentTools,
    FastMCPAgentsConfig,
    MCPConfigWithOverrides,
    RemoteMCPServerWithOverrides,
    StdioMCPServerWithOverrides,
    load_agents,
)
from fastmcp_agents.observability.logging import BASE_LOGGER
from fastmcp_agents.vendored.tool_transformer.loader import proxy_mcp_server_with_overrides

logger = BASE_LOGGER.getChild("main")

ROOT_LOGGER = logging.getLogger()

ROOT_LOGGER.setLevel(logging.WARNING)

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None:
    from fastmcp_agents.observability.otel import setup_otel

    setup_otel()

MCP_TRANSPORT_HELP = """
The transport to use for the MCP server.

- stdio: Use the standard input and output streams.
- sse: Use Server-Sent Events.
- streamable-http: Use the Streamable HTTP transport.
"""


def split_config(config: FastMCPAgentsConfig) -> tuple[MCPConfigWithOverrides, ContentTools, list[AgentConfig]]:
    mcp_config_with_overrides = MCPConfigWithOverrides(mcpServers=config.mcpServers)
    content_tools = ContentTools(tools=config.tools)
    return mcp_config_with_overrides, content_tools, config.agents


def get_config_from_url(config_url: str) -> tuple[MCPConfigWithOverrides, ContentTools, list[AgentConfig]]:
    config_raw = requests.get(config_url, timeout=10).text
    config = FastMCPAgentsConfig.model_validate(yaml.safe_load(config_raw))
    return split_config(config)


def get_config_from_file(config_file: str) -> tuple[MCPConfigWithOverrides, ContentTools, list[AgentConfig]]:
    if not Path(config_file).exists():
        msg = f"Config file {config_file} not found"
        raise FileNotFoundError(msg)
    config_raw = Path(config_file).read_text(encoding="utf-8")
    config = FastMCPAgentsConfig.model_validate(yaml.safe_load(config_raw))
    return split_config(config)


def get_config_from_bundled(config_bundled: str) -> tuple[MCPConfigWithOverrides, ContentTools, list[AgentConfig]]:
    bundled_dir = Path(__file__).parent.parent / "bundled" / "servers"
    bundled_server_settings_path: Path = bundled_dir / f"{config_bundled}.yml"

    if not bundled_server_settings_path.exists():
        msg = f"Bundled server config file {bundled_server_settings_path} not found"
        raise FileNotFoundError(msg)

    config_raw = bundled_server_settings_path.read_text(encoding="utf-8")

    config = FastMCPAgentsConfig.model_validate(yaml.safe_load(config_raw))
    return split_config(config)


async def prepare_mcp_servers(
    tool_server: FastMCP, mcp_servers_with_overrides: dict[str, StdioMCPServerWithOverrides | RemoteMCPServerWithOverrides]
) -> tuple[dict[str, Client], dict[str, FastMCP]]:
    """Prepare the MCP servers with Tool overrides.

    Args:
        tool_server: The server to mount the tools into.
        mcp_servers_with_overrides: The MCP servers with overrides.

    Returns:
        The MCP servers.
    """
    mcp_servers: dict[str, FastMCP] = {}
    mcp_clients: dict[str, Client] = {}

    for mcp_server_name, mcp_server_settings in mcp_servers_with_overrides.items():
        logger.info("Preparing MCP server %s", mcp_server_name)
        overrides = mcp_server_settings.get_tool_overrides()

        mcp_client, mcp_server = await proxy_mcp_server_with_overrides(
            mcp_server_name, mcp_server_settings, tool_overrides=overrides, target_server=tool_server
        )

        mcp_clients[mcp_server_name] = mcp_client
        mcp_servers[mcp_server_name] = mcp_server

        mcp_server_tools = await mcp_server.get_tools()
        mcp_server_tools_names = [tool.name for tool in mcp_server_tools.values()]
        logger.info(
            f"MCP server {mcp_server_name} offers {len(mcp_server_tools)} tools: {mcp_server_tools_names} ({len(overrides)} overriden)."
        )

    return mcp_clients, mcp_servers


async def prepare_server(
    server_name: str,
    mcp_config_with_overrides: MCPConfigWithOverrides,
    agents_config: list[AgentConfig],
    content_tools: ContentTools,
    agent_only: bool,
    tool_only: bool,
) -> tuple[dict[str, Client], dict[str, FastMCP], FastMCP]:
    """Prepare the server for the agents and tools.

    Args:
        server_name: The name of the server.
        agents_config: The agents config.
        agent_only: Whether to only expose the agents.
        tool_only: Whether to only expose the tools.
    """

    tools_server = FastMCP(name=server_name)

    mcp_clients, mcp_servers = await prepare_mcp_servers(tools_server, mcp_config_with_overrides.mcpServers)

    for tool_name, tool_config in content_tools.tools.items():

        def content_tool_factory(content: str):
            def content_tool() -> str:
                return content

            return content_tool

        tools_server.add_tool(fn=content_tool_factory(tool_config.returns), name=tool_name, description=tool_config.description)

    tools_server_tools = await tools_server.get_tools()
    tools_server_tools_names = [tool.name for tool in tools_server_tools.values()]

    if tool_only:
        logger.info(f"Tool-only server with {len(tools_server_tools)} tools: {tools_server_tools_names}.")
        return mcp_clients, mcp_servers, tools_server

    agents_server = tools_server

    if agent_only:
        agents_server = FastMCP(name="agents")

    agents = load_agents(agents_config, tools=list(tools_server_tools.values()))
    agent_names = [agent.name for agent in agents]

    for agent in agents:
        agents_server.add_tool(fn=agent.currate, name=agent.name, description=agent.description)

    if agent_only:
        logger.info(f"Agent-only server with {len(agents)} agents: {agent_names}.")
    else:
        logger.info(f"Server with {len(agents)} agents: {agent_names} and {len(tools_server_tools)} tools: {tools_server_tools_names}.")

    return mcp_clients, mcp_servers, agents_server
