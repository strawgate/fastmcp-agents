"""Base CLI for FastMCP Agents."""

import asyncio
import json
import os
import sys
from typing import Any, Literal

import asyncclick as click
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.logging import configure_logging
from mcp.types import EmbeddedResource, ImageContent, TextContent
from pydantic import BaseModel, Field

from fastmcp_agents.agent.fastmcp import FastMCPAgent
from fastmcp_agents.cli.loader import get_config_for_bundled, get_config_from_file, get_config_from_url
from fastmcp_agents.cli.models import (
    AgentModel,
    AugmentedServerModel,
    OverriddenStdioMCPServer,
    ServerSettings,
)
from fastmcp_agents.errors.base import ContributionsWelcomeError
from fastmcp_agents.errors.cli import FastMCPAgentsError, NoConfigError
from fastmcp_agents.observability.logging import get_logger, setup_logging

logger = get_logger("cli")

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None:
    from fastmcp_agents.observability.otel import setup_otel

    setup_otel()


class PendingToolCall(BaseModel):
    """A pending tool call. Only used in the CLI class."""

    name: str
    arguments: dict[str, Any]


class ToolCallResult(PendingToolCall):
    """A result of a tool call. Only used in the CLI class."""

    name: str
    arguments: dict[str, Any]
    result: list[TextContent | ImageContent | EmbeddedResource]


class CliContext(BaseModel):
    """A context object that gets passed around the CLI commands."""

    server_settings: ServerSettings
    augmented_server_model: AugmentedServerModel = Field(default_factory=AugmentedServerModel)
    pending_tool_calls: list[PendingToolCall] = Field(default_factory=list)


@click.group()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="The transport to use for the MCP server. (stdio, sse, streamable-http)",
)
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

    # Setup FastMCP Agents Logging
    setup_logging(level=log_level)

    # Setup FastMCP Logging
    configure_logging(level=log_level, enable_rich_tracebacks=False)

    ctx.obj = CliContext(
        server_settings=ServerSettings(
            transport=transport,
            log_level=log_level,
            agent_only=agent_only,
            tool_only=tool_only,
        )
    )


@cli_base.group(name="cli", chain=True)
def cli_interface():
    """The group for the `CLI` part of the FastMCP Agents CLI.

    This allows building agents and wrapping servers entirely from the command line.
    """


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

    cli_context.augmented_server_model.agents.append(
        AgentModel(
            name=name,
            description=description,
            instructions=instructions,
            allowed_tools=split_allowed_tools,
            blocked_tools=split_blocked_tools,
        )
    )


@cli_base.group(name="config", chain=True)
@click.option("--file", type=str, help="The config file to use.")
@click.option("--url", type=str, help="The URL of the config file to use.")
@click.option(
    "--directory",
    envvar="FASTMCP_AGENTS_CONFIG_DIR",
    type=click.Path(exists=True),
    help="A directory of config files, from which --file is relative to",
)
@click.option("--bundled", type=str, help="The bundled server to use.")
@click.pass_context
def cli_with_config(
    ctx: click.Context, file: str | None = None, url: str | None = None, bundled: str | None = None, directory: str | None = None
):
    """Load a config file from the command line."""

    cli_context: CliContext = ctx.obj

    if url:
        cli_context.augmented_server_model = get_config_from_url(url)
    elif file:
        cli_context.augmented_server_model = get_config_from_file(directory=directory, file=file)
    elif bundled:
        cli_context.augmented_server_model = get_config_for_bundled(bundled)
    else:
        raise NoConfigError


async def handle_pending_tool_calls(
    mcp_clients: list[Client], server: FastMCP, pending_tool_calls: list[PendingToolCall]
) -> list[ToolCallResult]:
    results: list[ToolCallResult] = []

    server_client = Client(transport=server)

    async with server_client:
        for pending_tool_call in pending_tool_calls:
            try:
                result = await server_client.call_tool(pending_tool_call.name, pending_tool_call.arguments)
                tool_call_result = ToolCallResult(name=pending_tool_call.name, arguments=pending_tool_call.arguments, result=result)
                results.append(tool_call_result)
            except ToolError:  # noqa: PERF203
                logger.error(f"Tool {pending_tool_call.name} with arguments {pending_tool_call.arguments} returned an error.")  # noqa: TRY400

    for mcp_client in mcp_clients:
        await mcp_client.close()

    for result in results:
        logger.info(f"Tool {result.name} with arguments {result.arguments} returned result:\n{result.result}")

    return results


async def run_server_or_call_tools(
    agents: list[FastMCPAgent],
    mcp_clients: list[Client],
    server: FastMCP,
    pending_tool_calls: list[PendingToolCall],
    transport: Literal["stdio", "sse", "streamable-http"],
):
    """A shared helper for either running the server or handling pending tool calls."""
    if pending_tool_calls:
        await handle_pending_tool_calls(mcp_clients, server, pending_tool_calls)
    else:
        await server.run_async(transport=transport)

    total_token_usage = sum(agent.llm_link.token_usage for agent in agents)
    logger.info(f"Total token usage: {total_token_usage}")


@cli_with_config.command(name="run")
@click.pass_context
async def cli_with_config_run(ctx: click.Context):
    """Run the server with configuration from a config source."""
    cli_context: CliContext = ctx.obj

    agents, mcp_clients, server = await cli_context.augmented_server_model.to_fastmcp_server(server_settings=cli_context.server_settings)

    await run_server_or_call_tools(
        agents=agents,
        mcp_clients=mcp_clients,
        server=server,
        pending_tool_calls=cli_context.pending_tool_calls,
        transport=cli_context.server_settings.transport,
    )


@cli_interface.command(name="list")
@click.pass_context
async def list_tools(
    ctx: click.Context,
):
    """List the tools available on the server."""
    cli_context: CliContext = ctx.obj

    _, mcp_clients, server = await cli_context.augmented_server_model.to_fastmcp_server(server_settings=cli_context.server_settings)

    tools = await server.get_tools()

    for mcp_client in mcp_clients:
        await mcp_client.close()

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


@cli_base.command(name="shell")
@click.pass_context
def shell(ctx: click.Context):  # noqa: ARG001
    """
    Start a shell session with the server.

    NOTE: This feature is currently unimplemented. Contributions are welcome!
    """
    raise ContributionsWelcomeError(feature="shell")


@cli_interface.command(name="wrap", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.option("--env", type=str, multiple=True, help="The environment variables to set for the server.")
@click.argument("direct-wrap-args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
async def wrap_server_run_mcp(
    ctx: click.Context,
    env: list[str],
    direct_wrap_args: list[str],
):
    """Take the last of the cli args and use them to run the mcp server and run it."""
    cli_context: CliContext = ctx.obj

    command = direct_wrap_args[0]
    args = direct_wrap_args[1:] if len(direct_wrap_args) > 1 else []
    environment = os.environ.copy()

    for env_var in env:
        key, value = env_var.split("=")
        environment[key] = value

    cli_context.augmented_server_model.mcpServers = {
        "main": OverriddenStdioMCPServer(
            command=command,
            args=args,
            env=environment,
        )
    }

    agents, mcp_clients, server = await cli_context.augmented_server_model.to_fastmcp_server(server_settings=cli_context.server_settings)

    await run_server_or_call_tools(
        agents=agents,
        mcp_clients=mcp_clients,
        server=server,
        pending_tool_calls=cli_context.pending_tool_calls,
        transport=cli_context.server_settings.transport,
    )


cli_with_config.add_command(call_tool)
cli_with_config.add_command(list_tools)


def run_mcp():
    try:
        asyncio.run(cli_base())
    except FastMCPAgentsError:
        logger.exception(msg="An error occurred while running FastMCPAgents")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        sys.exit(0)
    except Exception:
        logger.exception(msg="An unknown error occurred while running FastMCPAgents")
        sys.exit(1)


if __name__ == "__main__":
    run_mcp()
