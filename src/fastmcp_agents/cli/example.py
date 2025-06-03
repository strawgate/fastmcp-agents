"""Sample code for FastMCP using InterceptingProxyTool."""

import asyncio
from typing import TYPE_CHECKING

from fastmcp.client import Client

if TYPE_CHECKING:
    from fastmcp.tools import Tool as FastMCPTool

third_party_mcp_config = {
    "time": {
        "command": "uvx",
        "args": [
            "git+https://github.com/modelcontextprotocol/servers.git@2025.4.24#subdirectory=src/time",
            "--local-timezone=America/New_York",
        ],
    }
}


async def async_main():
    client = Client(third_party_mcp_config, timeout=30)

    client_tools = await client.list_tools()
    client_tools_by_name = {tool.name: tool for tool in client_tools}

    convert_time_tool: FastMCPTool = client_tools_by_name["convert_time"]

    convert_time_tool.run(arguments={"source_timezone": "America/New_York", "time": "3:00", "target_timezone": "America/Los_Angeles"})


def run_mcp():
    asyncio.run(async_main())


if __name__ == "__main__":
    run_mcp()
