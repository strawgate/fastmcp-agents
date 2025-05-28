from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
import functools
import os
from pathlib import Path
from typing import Literal

import asyncclick as click
import requests
import litellm
import yaml
from fastmcp import Client, FastMCP
from fastmcp.utilities.logging import configure_logging
from fastmcp.utilities.mcp_config import MCPConfig

from fastmcp_agents.agent.loader import (
    Config,
    ContentTools,
    ExtraToolsAndOverrides,
    MCPServerConnection,
    RemoteMCPServerWithOverrides,
    StdioMCPServerWithOverrides,
    load_agents,
)
from fastmcp_agents.agent.observability.logging import BASE_LOGGER
from fastmcp_agents.tool_transformer.loader import ToolOverrides, transform_tools_from_server

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
        if not Path(config_file).exists():
            msg = f"Config file {config_file} not found"
            raise FileNotFoundError(msg)
        config_raw = Path(config_file).read_text(encoding="utf-8")

    return Config.model_validate(yaml.safe_load(config_raw))




async def transfer_tools_to_server(
    server_name: str, server_config: StdioMCPServerWithOverrides | RemoteMCPServerWithOverrides, frontend_server: FastMCP
):
    logger.info("Transforming tools from %s to frontend server", server_name)

    if isinstance(server_config, StdioMCPServerWithOverrides) and isinstance(server_config.env, dict):
        # if "ALL" in server_config.env:
        server_config.env = dict(os.environ.items())

        # # limit to specific environment variables
        # for env_name, env_value in os.environ.items():
        #     if env_name not in server_config.env:
        #         server_config.env[env_name] = env_value

    mcp_client = Client(MCPConfig(mcpServers={server_name: server_config}), timeout=30.0)
    extra_tools_and_overrides = ExtraToolsAndOverrides(tools=server_config.tools)

    extra_tools: ContentTools = extra_tools_and_overrides.get_content_tools()
    tool_overrides: ToolOverrides = extra_tools_and_overrides.get_tool_overrides()

    connection = MCPServerConnection(server_name, server_config)
    await connection.connect()
    server = FastMCP.as_proxy(connection._client)

    backend_tools = await server.get_tools()
    logger.debug(f"Backend server: {server}, overrides: {tool_overrides}, tools: {backend_tools}")

    await transform_tools_from_server(server, frontend_server, overrides=tool_overrides)

    for tool_name, tool_config in extra_tools.tools.items():

        def content_tool_factory(content: str):
            def content_tool() -> str:
                return content

            return content_tool

        frontend_server.add_tool(fn=content_tool_factory(tool_config.returns), name=tool_name, description=tool_config.description)


def server_options(func):
    @click.option(
        "--log-level",
        type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
        envvar="LOG_LEVEL",
        default="INFO",
        help="The logging level to use for the agent.",
    )
    @click.option("--agent-only", is_flag=True, help="Only run the agents, don't expose the tools to the client.")
    @click.option("--tool-only", is_flag=True, help="Only run the tools, don't expose the agents to the client.")
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def transport_options(func):
    @click.option("--mcp-transport", type=click.Choice(["stdio", "sse", "streamable-http"]), default="stdio", help=MCP_TRANSPORT_HELP)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def provider_options(func):
    @click.option("--model", type=str, required=True, envvar="MODEL", help="The model to use for the agent.")
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper

def prompt_suggestions_dir_option(func):
    @click.option("--prompt-suggestions-dir", type=click.Path(file_okay=False, dir_okay=True, exists=True), envvar="PROMPT_SUGGESTIONS_DIR", help="The directory to store prompt suggestions.")
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

async def start_server(
    config: Config,
    mcp_transport: Literal["stdio", "sse", "streamable-http"],
    model: str,
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    agent_only: bool,
    tool_only: bool,
    prompt_suggestions_dir: Path | None = None,
):
    configure_logging(level=log_level, logger=BASE_LOGGER.getChild("FastMCP"))
    BASE_LOGGER.setLevel(log_level)

    tools_server = FastMCP(name="tools")
    # For each MCP Server, create a client and transform the tools onto the frontend server
    for server_name, server_config in config.mcpServers.items():
        await transfer_tools_to_server(server_name, server_config, tools_server)

    # Get the final tool list for the tools server
    tools = list((await tools_server.get_tools()).values())
    logger.info("Tools server now provides the following tools: %s", (await tools_server.get_tools()).keys())

    if tool_only:
        await tools_server.run_async(transport=mcp_transport)
        return

    agents_server = tools_server

    if agent_only:
        agents_server = FastMCP(name="agents")

    # Load our Agents
    agents = load_agents(config.agents, model, tools=tools)

    # Register them as tools on the frontend server
    for agent in agents:
        agent.suggest_prompt_improvements = prompt_suggestions_dir
        agent.register_as_tools(agents_server)

    # Run the agents server
    await agents_server.run_async(transport=mcp_transport)


@click.group()
async def cli():
    pass

@cli.group(name="run")
async def run_cli():
    pass

@cli.group(name="bundled")
async def bundled_cli():
    pass


@bundled_cli.command(name="server")
@click.argument("bundled-server")
@server_options
@transport_options
@provider_options
@prompt_suggestions_dir_option
async def run_bundled_server(
    mcp_transport: Literal["stdio", "sse", "streamable-http"],
    bundled_server: str,    
    # agent_config_file: str,
    model: str,
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    agent_only: bool,
    tool_only: bool,
    prompt_suggestions_dir: Path | None = None,
):
    #litellm._turn_on_debug()
    # the bundled servers are in a `servers` directory right next to this file.

    bundled_dir = Path(__file__).parent / "servers"

    bundled_server_config_path: Path = bundled_dir / f"{bundled_server}.yml"

    if not bundled_server_config_path.exists():
        msg = f"Bundled server config file {bundled_server_config_path} not found"
        raise FileNotFoundError(msg)

    config = get_config(str(bundled_server_config_path))

    await start_server(config, mcp_transport, model, log_level, agent_only, tool_only, prompt_suggestions_dir)


@bundled_cli.command(name="flow")
@click.argument("bundled-flow")
@server_options
@transport_options
@provider_options
@prompt_suggestions_dir_option
async def run_bundled_flow(
    mcp_transport: Literal["stdio", "sse", "streamable-http"],
    bundled_flow: str,
    # agent_config_file: str,
    model: str,
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    agent_only: bool,
    tool_only: bool,
    prompt_suggestions_dir: Path | None = None,
):

    # the bundled servers are in a `servers` directory right next to this file.

    bundled_dir = Path(__file__).parent / "flows"

    bundled_flow_config_path: Path = bundled_dir / f"{bundled_flow}.yml"

    if not bundled_flow_config_path.exists():
        msg = f"Bundled flow config file {bundled_flow_config_path} not found"
        raise FileNotFoundError(msg)

    config = get_config(str(bundled_flow_config_path))

    await start_server(config, mcp_transport, model, log_level, agent_only, tool_only, prompt_suggestions_dir)



@run_cli.command(name="config")
@click.option(
    "--config-file",
    type=str,
    help="The config file to use. Can be a local file or a URL. This is the config for the MCP Servers, tool overrides, and agents.",
)
@click.option(
    "--config-url", type=str, help="The URL of the config file to use. This is the config for the MCP Servers, tool overrides, and agents."
)
@server_options
@transport_options
@provider_options
@prompt_suggestions_dir_option
async def run_config(
    mcp_transport: Literal["stdio", "sse", "streamable-http"],
    config_file: str,
    # agent_config_file: str,
    model: str,
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    agent_only: bool,
    tool_only: bool,
    prompt_suggestions_dir: Path | None = None,
):
    pass


def run_mcp():
    asyncio.run(cli())


if __name__ == "__main__":
    run_mcp()
