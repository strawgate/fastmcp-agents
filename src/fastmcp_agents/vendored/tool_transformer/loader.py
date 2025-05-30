import json
import os
from pathlib import Path
from typing import Any

import yaml
from fastmcp import Client
from fastmcp.server.server import FastMCP
from fastmcp.utilities.mcp_config import MCPConfig, RemoteMCPServer, StdioMCPServer

from fastmcp_agents.vendored.tool_transformer.models import ToolOverride
from fastmcp_agents.vendored.tool_transformer.tool_transformer import proxy_tool


def overrides_from_dict(obj: dict[str, Any]) -> dict[str, ToolOverride]:
    return {tool_name: ToolOverride.model_validate(tool_override) for tool_name, tool_override in obj.items()}


def overrides_from_yaml(yaml_str: str) -> dict[str, ToolOverride]:
    return overrides_from_dict(yaml.safe_load(yaml_str))


def overrides_from_yaml_file(yaml_file: Path) -> dict[str, ToolOverride]:
    with Path(yaml_file).open(encoding="utf-8") as f:
        return overrides_from_yaml(yaml_str=f.read())


def overrides_from_json(json_str: str) -> dict[str, ToolOverride]:
    return overrides_from_dict(json.loads(json_str))


def overrides_from_json_file(json_file: Path) -> dict[str, ToolOverride]:
    with Path(json_file).open(encoding="utf-8") as f:
        return overrides_from_json(f.read())


async def proxy_mcp_server_with_overrides(
    server_name: str,
    server_config: StdioMCPServer | RemoteMCPServer,
    tool_overrides: dict[str, ToolOverride],
    client_kwargs: dict[str, Any] | None = None,
    server_kwargs: dict[str, Any] | None = None,
    target_server: FastMCP | None = None,
) -> tuple[Client, FastMCP]:
    """Run a MCP server with overrides."""

    if client_kwargs is None:
        client_kwargs = {}
    if server_kwargs is None:
        server_kwargs = {}
    if target_server is None:
        target_server = FastMCP(name="tools")

    if isinstance(server_config, StdioMCPServer):
        server_config.env = {**server_config.env, **os.environ}

    mcp_config = MCPConfig(mcpServers={server_name: server_config})

    mcp_client = Client(mcp_config, init_timeout=60.0, **client_kwargs)

    mcp_proxy_server = FastMCP.as_proxy(mcp_client, **server_kwargs)

    server_tools = await mcp_proxy_server.get_tools()

    for tool in server_tools.values():
        proxy_tool(tool, target_server, override=tool_overrides.get(tool.name))

    return mcp_client, target_server
