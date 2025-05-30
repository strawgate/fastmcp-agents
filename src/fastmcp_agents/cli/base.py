import asyncio
import json
import logging
import os
from typing import Any, Literal

import asyncclick as click
from fastmcp import Client
from fastmcp.utilities.logging import configure_logging
from pydantic import BaseModel, Field

from fastmcp_agents.cli.models import (
    AgentConfig,
    ContentTools,
    MCPConfigWithOverrides,
    ServerSettings,
    StdioMCPServerWithOverrides,
)
from fastmcp_agents.cli.utils import get_config_from_bundled, get_config_from_file, get_config_from_url, prepare_server
from fastmcp_agents.errors.cli import NoConfigError
from fastmcp_agents.observability.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("main")

ROOT_LOGGER = logging.getLogger()

ROOT_LOGGER.setLevel(logging.WARNING)

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None:
    from fastmcp_agents.observability.otel import setup_otel

    setup_otel()


MCP_TRANSPORT_HELP = "The transport to use for the MCP server. (stdio, sse, streamable-http)"


class PendingToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]


class CliContext(BaseModel):
    server_settings: ServerSettings
    agents_config: list[AgentConfig] = Field(default_factory=list)
    mcp_config_with_overrides: MCPConfigWithOverrides = Field(default_factory=MCPConfigWithOverrides)
    content_tools: ContentTools = Field(default_factory=ContentTools)
    pending_tool_calls: list[PendingToolCall] = Field(default_factory=list)
    # frontend_server: FastMCP | None = None


@click.group()
@click.option("--transport", type=click.Choice(["stdio", "sse", "streamable-http"]), default="stdio", help=MCP_TRANSPORT_HELP)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="The logging level to use for the agent.",
)
@click.option("--agent-only", is_flag=True, help="Only run the agents, don't expose the tools to the client.")
@click.option("--tool-only", is_flag=True, help="Only run the tools, don't expose the agents to the client.")
@click.pass_context
def cli_base(
    ctx: click.Context,
    transport: Literal["stdio", "sse", "streamable-http"],
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    agent_only: bool = False,
    tool_only: bool = False,
):
    """The base CLI for the FastMCP Agents. Configure logging, transport, and filtering."""
    
    configure_logging(level=log_level, logger=BASE_LOGGER.getChild("FastMCP"))

    BASE_LOGGER.setLevel(log_level)

    ctx.obj = CliContext(
        server_settings=ServerSettings(
            transport=transport,
            log_level=log_level,
            agent_only=agent_only,
            tool_only=tool_only,
        )
    )


@cli_base.group(name="cli", chain=True)
@click.pass_context
def cli_interface(
    ctx: click.Context,
):
    """The group for the `CLI` part of the FastMCP Agents CLI."""


@cli_interface.command(name="agent")
@click.option("--name", help="The name of the agent to wrap.")
@click.option("--description", help="The description of the agent to wrap.")
@click.option("--instructions", help="The instructions of the agent to wrap.")
@click.option("--allowed-tools", help="A comma separated list of the tools that the agent can use.")
@click.option("--blocked-tools", help="A comma separated list of the tools that the agent cannot use.")
@click.pass_context
def cli_build_agent(
    ctx: click.Context,
    name: str,
    description: str,
    instructions: str,
    allowed_tools: str,
    blocked_tools: str,
):
    """Build an agent over the command line."""
    split_allowed_tools = allowed_tools.split(",") if allowed_tools else None
    split_blocked_tools = blocked_tools.split(",") if blocked_tools else None

    cli_context: CliContext = ctx.obj

    cli_context.agents_config.append(
        AgentConfig(
            name=name,
            description=description,
            default_instructions=instructions,
            allowed_tools=split_allowed_tools,
            blocked_tools=split_blocked_tools,
        )
    )


@cli_base.command(name="config")
@click.option("--file", type=click.Path(exists=True), help="The config file to use.")
@click.option("--url", type=str, help="The URL of the config file to use.")
@click.option("--bundled", type=str, help="The bundled server to use.")
@click.pass_context
async def cli_with_config(ctx: click.Context, file: str | None = None, url: str | None = None, bundled: str | None = None):
    """Load a config file from the command line."""

    cli_context: CliContext = ctx.obj

    server_settings: ServerSettings = cli_context.server_settings

    mcp_servers_with_overrides: MCPConfigWithOverrides = MCPConfigWithOverrides()
    agents_config: list[AgentConfig] = []
    if url:
        mcp_servers_with_overrides, content_tools, agents_config = get_config_from_url(url)
    elif file:
        mcp_servers_with_overrides, content_tools, agents_config = get_config_from_file(file)
    elif bundled:
        mcp_servers_with_overrides, content_tools, agents_config = get_config_from_bundled(bundled)
    else:
        raise NoConfigError

    _, _, server = await prepare_server(
        server_name="wrap",
        mcp_config_with_overrides=mcp_servers_with_overrides,
        agents_config=agents_config,
        content_tools=content_tools,
        agent_only=server_settings.agent_only,
        tool_only=server_settings.tool_only,
    )

    await server.run_async(transport=server_settings.transport)


@cli_interface.command(name="list")
@click.pass_context
async def list_tools(
    ctx: click.Context,
):
    """List the tools available on the server."""
    cli_context: CliContext = ctx.obj

    _, _, server = await prepare_server(
        server_name="wrap",
        mcp_config_with_overrides=cli_context.mcp_config_with_overrides,
        agents_config=cli_context.agents_config,
        content_tools=cli_context.content_tools,
        agent_only=cli_context.server_settings.agent_only,
        tool_only=cli_context.server_settings.tool_only,
    )

    tools = await server.get_tools()

    logger.info("Listing tools:")
    for tool in tools.values():
        logger.info(f"Tool: {tool.name}")


@cli_interface.command(name="call", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("name", type=str)
@click.argument("parameters", type=str)
@click.pass_context
def call_tool(
    ctx: click.Context,
    name: str,
    parameters: str,
):
    """Add a tool call to the pending tool calls list."""
    cli_context: CliContext = ctx.obj

    arguments = json.loads(parameters)

    cli_context.pending_tool_calls.append(PendingToolCall(name=name, arguments=arguments))


@cli_interface.command(name="wrap", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("direct-wrap-args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
async def wrap_server_run_mcp(
    ctx: click.Context,
    direct_wrap_args: list[str],
):
    """Take the last of the cli args and use them to run the mcp serverand run it."""
    cli_context: CliContext = ctx.obj

    if cli_context.mcp_config_with_overrides is None:
        raise NoConfigError

    if cli_context.agents_config is None:
        raise NoConfigError

    if len(direct_wrap_args) == 0:
        logger.warning("No MCP Servers to wrap.")

    command = direct_wrap_args[0]
    args = direct_wrap_args[1:] if len(direct_wrap_args) > 1 else []
    env = os.environ.copy()

    mcp_config = MCPConfigWithOverrides(
        mcpServers={
            "main": StdioMCPServerWithOverrides(
                command=command,
                args=args,
                env=env,
            )
        }
    )

    _, _, server = await prepare_server(
        server_name="wrap",
        mcp_config_with_overrides=mcp_config,
        agents_config=cli_context.agents_config,
        content_tools=cli_context.content_tools,
        agent_only=cli_context.server_settings.agent_only,
        tool_only=cli_context.server_settings.tool_only,
    )

    if cli_context.pending_tool_calls:
        client = Client(server)
        async with client:
            tools = await server.get_tools()
            for pending_tool_call in cli_context.pending_tool_calls:
                tool = tools[pending_tool_call.name]
                result = await client.call_tool(tool.name, pending_tool_call.arguments)

                logger.info(f"Tool {pending_tool_call.name} result: {result}")

        await client.close()
    else:
        await server.run_async(transport=cli_context.server_settings.transport)


def run_mcp():
    asyncio.run(cli_base())


if __name__ == "__main__":
    run_mcp()
