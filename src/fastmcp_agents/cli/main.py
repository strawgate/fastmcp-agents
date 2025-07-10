"""Base CLI for FastMCP Agents."""

import asyncio
import json
import os
import sys
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import asyncclick as click
import fastmcp
from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.exceptions import ToolError
from mcp.types import ContentBlock
from pydantic import BaseModel, Field
from rich.console import Console
from rich.markdown import Markdown

from fastmcp_agents.agent.multi_step import MultiStepAgent
from fastmcp_agents.cli.models.agents import AgentModel
from fastmcp_agents.cli.models.config import (
    FastMCPAgentsConfig,
    FromBundledNestedServerConfig,
    FromFileNestedServerConfig,
    FromURLNestedServerConfig,
)
from fastmcp_agents.cli.models.servers import StdioMCPServerConfig
from fastmcp_agents.conversation.utils import join_content
from fastmcp_agents.errors.base import ContributionsWelcomeError, FastMCPAgentsError
from fastmcp_agents.errors.cli import NoConfigError
from fastmcp_agents.util.logging import get_logger, setup_logging

warnings.filterwarnings("ignore", category=DeprecationWarning)
logger = get_logger("cli")

DEFAULT_INIT_TIMEOUT = 60


class ServerSettings(BaseModel):
    """Settings for the server."""

    transport: Literal["stdio", "sse", "streamable-http"] = Field(..., description="The transport to use for the server.")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(..., description="The log level to use for the server.")
    agent_only: bool = Field(default=False, description="Whether to only run the agents.")
    tool_only: bool = Field(default=False, description="Whether to only run the tools.")
    mutable_agents: bool = Field(default=False, description="Whether to publish a tool to mutate the Agent's System Prompt.")


class PendingToolCall(BaseModel):
    """A pending tool call. Only used in the CLI class."""

    name: str
    arguments: dict[str, Any]
    print_format: Literal["markdown", "text", "none"] = "text"
    file: Path | None = None


class ToolCallResult(PendingToolCall):
    """A result of a tool call. Only used in the CLI class."""

    result: list[ContentBlock]


class CliContext(BaseModel):
    """A context object that gets passed around the CLI commands."""

    server_settings: ServerSettings
    server_config: FastMCPAgentsConfig = Field(default_factory=FastMCPAgentsConfig)
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
@click.option("--py-warnings", is_flag=True, help="Show built-in Python warnings.")
@click.option("--show-tracebacks", is_flag=True, help="Show tracebacks for errors.")
@click.option("--mutable-agents", is_flag=True, help="Publish a tool to mutate the Agent's Instructions.")
@click.option("--agent-only", is_flag=True, help="Only run the agents, don't expose the tools to the client.")
@click.option("--tool-only", is_flag=True, help="Only run the tools, don't expose the agents to the client.")
@click.pass_context
def cli_base(
    ctx: click.Context,
    transport: Literal["stdio", "sse", "streamable-http"],
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    agent_only: bool = False,
    tool_only: bool = False,
    mutable_agents: bool = False,
    py_warnings: bool = False,
    show_tracebacks: bool = False,
):
    """The base CLI for the FastMCP Agents. Configure logging, transport, and filtering."""

    if py_warnings:
        warnings.resetwarnings()

    # Setup FastMCP Agents Logging
    setup_logging(level=log_level, show_tracebacks=show_tracebacks)

    fastmcp.settings.enable_rich_tracebacks = False
    # configure_logging(level=log_level, enable_rich_tracebacks=False)

    ctx.obj = CliContext(
        server_settings=ServerSettings(
            transport=transport,
            log_level=log_level,
            agent_only=agent_only,
            tool_only=tool_only,
            mutable_agents=mutable_agents,
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

    cli_context: CliContext = ctx.obj  # pyright: ignore[reportAny]

    cli_context.server_config.agents.append(
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
async def cli_with_config(
    ctx: click.Context, file: str | None = None, url: str | None = None, bundled: str | None = None, directory: str | None = None
):
    """Load a config file from the command line."""

    cli_context: CliContext = ctx.obj

    if url:
        cli_context.server_config = await FromURLNestedServerConfig(url=url).load()
    elif file:
        cli_context.server_config = await FromFileNestedServerConfig(file=file).load()
    elif bundled:
        cli_context.server_config = await FromBundledNestedServerConfig(bundle=bundled).load()
    else:
        raise NoConfigError


async def handle_pending_tool_calls(
    server: FastMCP[Any], pending_tool_calls: list[PendingToolCall]
) -> list[ToolCallResult]:
    results: list[ToolCallResult] = []

    server_client = Client(transport=server, init_timeout=DEFAULT_INIT_TIMEOUT)
    console = Console()

    async with server_client:
        for pending_tool_call in pending_tool_calls:
            try:
                result = await server_client.call_tool(pending_tool_call.name, pending_tool_call.arguments)

                tool_call_result = ToolCallResult(
                    name=pending_tool_call.name,
                    arguments=pending_tool_call.arguments,
                    result=result.content,
                    print_format=pending_tool_call.print_format,
                    file=pending_tool_call.file,
                )

                if write_to_file := tool_call_result.file:
                    _ = write_to_file.write_text(join_content(result.content), encoding="utf-8")

                if tool_call_result.print_format == "markdown":
                    console.print(Markdown(join_content(result.content)))

                if tool_call_result.print_format == "text":
                    console.print(join_content(result.content))

                results.append(tool_call_result)
            except ToolError:  # noqa: PERF203
                logger.exception(f"Tool {pending_tool_call.name} with arguments {pending_tool_call.arguments} returned an error.")

    # for result in results:
    #     if result.file is not None:
    #         content = join_content(result.result)
    #         result.file.write_text(content, encoding="utf-8")

    #     if result.print_format == "none":
    #         continue

    #     console = Console()
    #     console.print(f"Tool {result.name} with arguments {result.arguments} returned result:")

    #     content = join_content(result.result)
    #     if result.print_format == "markdown":
    #         console.print(Markdown(content))

    #     if result.print_format == "text":
    #         console.print(content)

    return results


async def run_server_or_call_tools(
    agents: Sequence[MultiStepAgent],
    mcp_clients: Sequence[Client[Any]],
    fastmcp_server: FastMCP[Any],
    pending_tool_calls: list[PendingToolCall],
    transport: Literal["stdio", "sse", "streamable-http"],
):
    """A shared helper for either running the server or handling pending tool calls."""

    try:
        if pending_tool_calls:
            _ = await handle_pending_tool_calls(server=fastmcp_server, pending_tool_calls=pending_tool_calls)
        else:
            await fastmcp_server.run_async(transport=transport)
    finally:
        total_token_usage = sum(agent.llm_link.get_token_usage() for agent in agents)
        logger.info(f"Total token usage: {total_token_usage}")

        for mcp_client in mcp_clients:
            await mcp_client.close()

    print("Server closed")


@cli_with_config.command(name="run")
@click.pass_context
async def cli_with_config_run(ctx: click.Context):
    """Run the server with configuration from a config source."""
    cli_context: CliContext = ctx.obj

    fastmcp_server, activated_agents, activated_tools, nested_servers, mcp_servers, mcp_clients = await cli_context.server_config.activate()

    await run_server_or_call_tools(
        agents=activated_agents,
        mcp_clients=mcp_clients,
        fastmcp_server=fastmcp_server,
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

    fastmcp_server, _, _, _, _, _ = await cli_context.server_config.activate()

    tools = await fastmcp_server.get_tools()

    logger.info("Listing tools:")
    for tool in tools.values():
        logger.info(f"Tool: {tool.name}")


@cli_interface.command(name="call", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("name", type=str)
@click.argument("parameters", type=str)
@click.option(
    "--print",
    "print_format",
    type=click.Choice(["markdown", "text", "none"]),
    default="markdown",
    help="The format to use when printing the result.",
)
@click.option("--file", type=click.Path(path_type=Path), help="The file to write the result to.")
@click.pass_context
def call_tool(
    ctx: click.Context,
    name: str,
    parameters: str,
    print_format: Literal["markdown", "text", "none"],
    file: Path | None = None,
):
    """Add a tool call to the pending tool calls list."""
    cli_context: CliContext = ctx.obj

    arguments = json.loads(parameters)

    cli_context.pending_tool_calls.append(PendingToolCall(name=name, arguments=arguments, print_format=print_format, file=file))


@cli_base.command(name="shell")
@click.pass_context
def shell(ctx: click.Context):
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

    cli_context.server_config.mcp = {
        "main": StdioMCPServerConfig(
            command=command,
            args=args,
            env=environment,
        )
    }

    fastmcp_server, activated_agents, activated_tools, nested_servers, mcp_servers, mcp_clients = await cli_context.server_config.activate()

    await run_server_or_call_tools(
        agents=activated_agents,
        mcp_clients=mcp_clients,
        fastmcp_server=fastmcp_server,
        pending_tool_calls=cli_context.pending_tool_calls,
        transport=cli_context.server_settings.transport,
    )


cli_with_config.add_command(call_tool)
cli_with_config.add_command(list_tools)


def run():
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
    run()
