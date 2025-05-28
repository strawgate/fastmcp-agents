"""Sample code for FastMCP using InterceptingProxyTool."""

import asyncio

from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp_agents.tool_transformer.loader import (
    ToolOverrides,
    transform_tools_from_server,
)

third_party_mcp_config = {
    "time": {
        "command": "uvx",
        "args": [
            "git+https://github.com/modelcontextprotocol/servers.git@2025.4.24#subdirectory=src/time",
            "--local-timezone=America/New_York",
        ],
    }
}

override_config_yaml = ToolOverrides.from_yaml("""
tools:
  convert_time:
    description: >-
        An updated multi-line description 
        for the time tool.
    parameter_overrides:
      source_timezone:
        description: This field now has a description and a constant value
        constant: America/New_York
      time:
        description: This field now has a description and a default value
        default: "3:00"
""")


async def async_main():
    async with Client(third_party_mcp_config) as remote_mcp_client:
        proxied_mcp_server = FastMCP.as_proxy(remote_mcp_client)

        frontend_server = FastMCP("Frontend Server")

        await transform_tools_from_server(
            proxied_mcp_server,
            frontend_server,
            overrides=override_config_yaml,
        )

        await frontend_server.run_async(transport="sse")


def run_mcp():
    asyncio.run(async_main())


if __name__ == "__main__":
    run_mcp()
