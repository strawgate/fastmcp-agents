from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Literal

import asyncclick as click
import requests
import yaml
from fastmcp import Client, FastMCP
from fastmcp.contrib.tool_transformer.loader import ToolOverrides, transform_tools_from_server
from fastmcp.utilities.logging import configure_logging
from fastmcp.utilities.mcp_config import MCPConfig

from fastmcp_agents.agent.loader import (
    Config,
    RemoteMCPServerWithOverrides,
    StdioMCPServerWithOverrides,
    load_agents,
)
from fastmcp_agents.agent.observability.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("main")


MCP_TRANSPORT_HELP = """
The transport to use for the MCP server.

- stdio: Use the standard input and output streams.
- sse: Use Server-Sent Events.
- streamable-http: Use the Streamable HTTP transport.
"""


def get_config(config_file: str) -> Config:
    config_raw: str
    if config_file.startswith("https://"):
        config_raw = requests.get(config_file, timeout=10).text
    else:
        config_raw = Path(config_file).read_text(encoding="utf-8")

    return Config.model_validate(yaml.safe_load(config_raw))


async def transfer_tools_to_frontend_server(server_name: str, server_config: StdioMCPServerWithOverrides | RemoteMCPServerWithOverrides, frontend_server: FastMCP):
    logger.info("Transforming tools from %s to frontend server", server_name)

    mcp_client = Client(MCPConfig(mcpServers={server_name: server_config}))
    tool_overrides = ToolOverrides(tools=server_config.tools)

    server = FastMCP.as_proxy(mcp_client)

    backend_tools = await server.get_tools()

    logger.info("Backend servers provides the following tools: %s", backend_tools.keys())
    logger.info("Transforming tools from backend server to frontend server: %s", tool_overrides.tools.keys())

    await transform_tools_from_server(server, frontend_server, overrides=tool_overrides)


@click.command()
@click.option(
    "--mcp-transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help=MCP_TRANSPORT_HELP,
)
@click.option(
    "--config-file",
    type=click.Path(exists=True),
    default="config.yaml",
    help="The config file to use. This is the config for the MCP Servers, tool overrides, and agents.",
)
# @click.option(
#     "--tool-overrides-file",
#     type=click.Path(exists=True),
#     default="tool_overrides.yaml",
#     help="The tool overrides file to use. This is the tool overrides that will be used to transform the tools.",
# )
# @click.option(
#     "--agent-config-file",
#     type=click.Path(exists=True),
#     required=True,
#     default="agent_config.yaml",
#     help="The agent config file to use. This is the agent that will be used to perform the task.",
# )
@click.option(
    "--model",
    type=str,
    required=True,
    help="The model to use for the agent.",
)
@click.option(
    "--logging-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="The logging level to use for the agent.",
)
async def cli(
    mcp_transport: Literal["stdio", "sse", "streamable-http"],
    config_file: str,
    # agent_config_file: str,
    model: str,
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
):
    configure_logging(level=logging_level, logger=BASE_LOGGER.getChild("FastMCP"))

    config = get_config(config_file)

    # Create a frontend server to provide tools and our Agents
    frontend_server = FastMCP(name="frontend")

    # For each MCP Server, create a client and transform the tools onto the frontend server
    for server_name, server_config in config.mcpServers.items():
        await transfer_tools_to_frontend_server(server_name, server_config, frontend_server)

    # Get the final tool list for the frontend server
    tools = list((await frontend_server.get_tools()).values())
    logger.info("Frontend servers now provides the following tools: %s", (await frontend_server.get_tools()).keys())

    # Load our Agents
    agents = load_agents(config.agents, model, tools=tools)

    # Register them as tools on the frontend server
    for agent in agents:
        agent.register_as_tools(frontend_server)

    # Run the frontend server
    await frontend_server.run_async(transport=mcp_transport)


def run_mcp():
    asyncio.run(cli())


if __name__ == "__main__":
    run_mcp()
