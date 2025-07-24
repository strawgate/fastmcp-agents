import json as pyjson
import os
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import yaml
from cyclopts import App
from cyclopts.parameter import Parameter
from fastmcp import Client, FastMCP
from fastmcp.client.transports import FastMCPTransport
from fastmcp.mcp_config import MCPConfig, StdioMCPServer, TransformingStdioMCPServer
from rich import print as rich_print
from rich.pretty import pprint as rich_pprint

from fastmcp_agents.cli.utils import rich_table_from_tools

if TYPE_CHECKING:
    from fastmcp.client.client import CallToolResult
    from fastmcp.server.proxy import FastMCPProxy
    from mcp.types import Tool


def try_default_configs() -> Path | None:
    """Try to find a default config file."""
    for config in ["mcp.json", "config.json", "mcp.yml", "config.yml"]:
        if Path(config).exists():
            return Path(config)

    return None


def try_config(config: Path | None) -> Path:
    """Try to find a config file."""
    if config:
        return config

    if config := try_default_configs():
        return config

    msg = "No config file found. Please specify a config file using the --config option."
    raise FileNotFoundError(msg)


app: App = App(name="FastMCP CLI")
app.command(call_app := App(name="call"))
app.command(list_app := App(name="list"))


def get_client(config: Path | None) -> Client[FastMCPTransport]:
    config = try_config(config=config)

    config_text: str = config.read_text()

    config_dict: dict[str, Any] = yaml.safe_load(config_text)

    mcp_config: MCPConfig = MCPConfig.from_dict(config=config_dict)

    for mcp_server_config in mcp_config.mcpServers.values():
        if isinstance(mcp_server_config, TransformingStdioMCPServer | StdioMCPServer):
            mcp_server_config.env = dict(os.environ.copy())

    server: FastMCPProxy = FastMCP.as_proxy(backend=mcp_config)

    client: Client[FastMCPTransport] = Client(server)

    return client


@list_app.command(name="tools")
async def list_tools(
    config: Annotated[Path | None, Parameter(help="Path to the MCP Configuration file.")] = None,
) -> None:
    """List tools available on the server."""
    async with get_client(config=config) as client:
        tools: list[Tool] = await client.list_tools()

        rich_table = rich_table_from_tools(tools=tools)
        rich_print(rich_table)


@call_app.command(name="tool")
async def call_tool(
    tool: Annotated[str, Parameter(help="The name of the tool to call")],
    config: Annotated[Path | None, Parameter(help="Path to the MCP Configuration file.")] = None,
    args: Annotated[str | None, Parameter(help="Arguments passed as JSON")] = None,
):
    """Call a tool with the given arguments."""

    async with get_client(config=config) as client:
        args_dict: dict[str, Any] = {}
        if isinstance(args, str):
            args_dict = pyjson.loads(s=args)

        result: CallToolResult = await client.call_tool(tool, arguments=args_dict)

        if result.data:
            rich_pprint(result.data)
        else:
            rich_print(result)

    return result


def run():
    app()


if __name__ == "__main__":
    run()
