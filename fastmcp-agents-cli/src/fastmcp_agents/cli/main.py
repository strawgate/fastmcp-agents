import asyncio
import json as pyjson
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal

import yaml
from cyclopts import App, Parameter
from fastmcp.client import Client
from fastmcp.client.client import CallToolResult
from fastmcp.client.transports import FastMCPTransport
from mcp.types import TextContent
from pydantic import BaseModel, Field
from rich import print as rich_print

from fastmcp_agents.cli.utils import rich_table_from_tools
from fastmcp_agents.core.models.server_builder import FastMCPAgents
from fastmcp_agents.core.observability.logging import reduce_fastmcp_logging, setup_logging

if TYPE_CHECKING:
    from rich.table import Table


DEFAULT_YAML_PATH = Path("mcp.yaml")
DEFAULT_YML_PATH = Path("mcp.yml")
DEFAULT_JSON_PATH = Path("mcp.json")


class CliConfigSource(BaseModel):
    """Context for the MCP client."""

    path: Path | None = Field(default=None, description="The MCP configuration file.")

    module: str | None = Field(default=None, description="The Python module to use for the MCP configuration file.")

    expand_vars: bool = Field(default=False, description="Whether to expand environment variables in the MCP configuration file.")

    def try_default_path(self) -> Path:
        """Try to find the default path."""

        if self.path is not None:
            return self.path

        return next(p for p in [DEFAULT_YAML_PATH, DEFAULT_YML_PATH, DEFAULT_JSON_PATH] if p.exists())


class CliLogOptions(BaseModel):
    """Context for the log settings."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", description="The log level to use for the CLI.")


class CliTagsOptions(BaseModel):
    """Context for the tags."""

    include: set[str] | None = Field(default=None, description="The tags to include in the server.")
    exclude: set[str] | None = Field(default=None, description="The tags to exclude from the server.")


logger = logging.getLogger(name="fastmcp_agents.cli")

root = App(name="FastMCP Agents Command Line Interface")

client_app = App(name="client", help="Run as an MCP Client and list/call tools.")
list_app = App(name="list", help="List the tools available on the server.")

call_app = App(name="call", help="Call a tool on the server.")

_ = client_app.command(list_app)
_ = client_app.command(call_app)


@root.command(name="shell")
def shell():
    """Run as an MCP Tool and call tools."""

    _ = client_app.interactive_shell(prompt="fastmcp-agents> ", quit=["exit", "quit", "q"])  # pyright: ignore[reportUnknownMemberType]


server_app = App(name="server", help="Run as an MCP Server and listen over the configured transport.")

_ = root.command(client_app)
_ = root.command(server_app)

DEFAULT_CLI_CONFIG_SOURCE = CliConfigSource()
DEFAULT_CLI_LOG_OPTIONS = CliLogOptions(level="INFO")
DEFAULT_OUTPUT_FORMAT = "rich"


# @server_app.command
# def sse(
#     model_options: Annotated[CliModelOptions, Parameter(name="model")] = DEFAULT_MODEL_OPTIONS,
#     config: Annotated[CliConfigSource, Parameter(name="config")] = DEFAULT_CLI_CONFIG_SOURCE,
#     port: Annotated[int, Parameter(name="port")] = 8000,
#     log_options: Annotated[CliLogOptions, Parameter(name="log")] = DEFAULT_CLI_LOG_OPTIONS,
# ):
#     """Run as an MCP Server and listen over SSE."""

#     setup_logging(level=log_options.level)

#     fastmcp = FastMCPAgents.from_yaml(config.try_default_path())

#     fastmcp.to_server(llm_completions=model_options.to_completions()).run(transport="sse", port=port, show_banner=False)


# @server_app.command
# def stdio(
#     model_options: Annotated[CliModelOptions, Parameter(name="model")] = DEFAULT_MODEL_OPTIONS,
#     config: Annotated[CliConfigSource, Parameter(name="config")] = DEFAULT_CLI_CONFIG_SOURCE,
# ):
#     """Run as an MCP Server and listen over stdio."""

#     fastmcp = FastMCPAgents.from_yaml(config.try_default_path())

#     fastmcp.to_server(llm_completions=model_options.to_completions()).run(transport="stdio", show_banner=False)


@list_app.command(name="tools")
def list_tools(
    *,
    config: Annotated[CliConfigSource, Parameter(name="config")] = DEFAULT_CLI_CONFIG_SOURCE,
    log_options: Annotated[CliLogOptions, Parameter(name="log")] = DEFAULT_CLI_LOG_OPTIONS,
    output_format: Annotated[
        Literal["json", "yaml", "rich"], Parameter(name="format", help="The format to output the tools in.")
    ] = DEFAULT_OUTPUT_FORMAT,
):
    """List the tools available on the server."""

    setup_logging(level=log_options.level)

    server = FastMCPAgents.from_yaml(config.try_default_path())

    server_client = server.to_client()

    async def call_list_tools(server_client: Client[Any]):
        """List the tools available on the server."""

        async with server_client:
            return await server_client.list_tools()

    tools = asyncio.run(call_list_tools(server_client))

    if output_format == "rich":
        table: Table = rich_table_from_tools(tools)
        rich_print(table)
        return

    raw_tools = [tool.model_dump(exclude_none=True) for tool in tools]
    if output_format == "json":
        print(pyjson.dumps(raw_tools, indent=2, sort_keys=False))
    elif output_format == "yaml":
        print(yaml.safe_dump(raw_tools, indent=2, sort_keys=False))


@call_app.command(name="tool")
def call_tool(
    tool_name: Annotated[str, Parameter(name="tool.name", help="The tool to call.")],
    *,
    config: Annotated[CliConfigSource, Parameter(name="config")] = DEFAULT_CLI_CONFIG_SOURCE,
    log_options: Annotated[CliLogOptions, Parameter(name="log")] = DEFAULT_CLI_LOG_OPTIONS,
    print_format: Annotated[Literal["json", "yaml", "rich"], Parameter(name="format", help="The format to output the result in.")] = "rich",
    output_file: Annotated[Path | None, Parameter(name="output", help="The file to save json output to.")] = None,
    json_arguments: Annotated[
        str | None,
        Parameter(name="json", help="The JSON arguments to pass to the tool. JSON Arguments will override other arguments."),
    ] = None,
    **tool_arguments: Annotated[Any, Parameter(help="The arguments to pass to the tool.")],  # pyright: ignore[reportAny]
):
    """Run the target MCP Server and perform a tool call."""

    setup_logging(level=log_options.level)

    fastmcp_agents_server = FastMCPAgents.from_yaml(config.try_default_path())

    fastmcp_server = fastmcp_agents_server.to_server()

    fastmcp_client = Client[FastMCPTransport](transport=fastmcp_server)

    reduce_fastmcp_logging()

    if json_arguments is not None:
        tool_arguments = pyjson.loads(json_arguments)  # pyright: ignore[reportAny]

    async def async_call_tool() -> CallToolResult:
        """Call a tool."""

        async with fastmcp_client:
            return await fastmcp_client.call_tool(tool_name, tool_arguments, raise_on_error=False)

    result = asyncio.run(async_call_tool())

    handle_tool_result(result, print_format, output_file)


def handle_tool_result(result: CallToolResult, print_format: Literal["json", "yaml", "rich"], output_file: Path | None):
    content: list[Any] | Any = []

    if not result.data:  # pyright: ignore[reportAny]
        for content_block in result.content:
            if isinstance(content_block, TextContent):
                _ = content.append(content_block.text)
                continue

            logger.warning(f"Unhandled non-text content block: {content_block}")
    else:
        content = result.data  # pyright: ignore[reportAny]

    match print_format:
        case "rich":
            try:
                from rich_tables import table

                _ = table.draw_data([content])
            except Exception:
                rich_print(content)
        case "json":
            print(pyjson.dumps(content, indent=2, sort_keys=False))
        case "yaml":
            print(yaml.safe_dump(content, indent=2, sort_keys=False))

    if output_file is not None:
        _ = output_file.write_text(pyjson.dumps(content, indent=2, sort_keys=False))


if __name__ == "__main__":
    try:
        root()
    except Exception:
        logger.exception("An error occurred while running the CLI.")
