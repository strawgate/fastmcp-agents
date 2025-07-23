from fastmcp import FastMCP
from fastmcp.client import Client, FastMCPTransport
from fastmcp.mcp_config import MCPConfig
from fastmcp.server.proxy import FastMCPProxy
from mcp.types import Tool


async def assert_mcp_init(mcp_config: MCPConfig) -> tuple[Client[FastMCPTransport], FastMCPProxy, list[Tool]]:
    fastmcp: FastMCPProxy = FastMCP.as_proxy(backend=mcp_config)

    client: Client[FastMCPTransport] = Client(fastmcp)

    async with client:
        tools: list[Tool] = await client.list_tools()

    assert tools

    return client, fastmcp, tools
