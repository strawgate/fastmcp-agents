from typing import TYPE_CHECKING

import pytest
from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from fastmcp.server.proxy import FastMCPProxy

from fastmcp_agents.library.mcp.strawgate import read_only_knowledge_base_mcp, read_write_knowledge_base_mcp

if TYPE_CHECKING:
    from fastmcp.client.transports import FastMCPTransport
    from fastmcp.server.proxy import FastMCPProxy
    from mcp.types import Tool


@pytest.mark.asyncio
async def test_read_only_init():
    fastmcp: FastMCPProxy = FastMCP.as_proxy(backend={"rokbmcp": read_only_knowledge_base_mcp()})

    client: Client[FastMCPTransport] = Client(fastmcp)

    async with client:
        tools: list[Tool] = await client.list_tools()

    assert tools is not None


@pytest.mark.asyncio
async def test_read_write_init():
    fastmcp: FastMCPProxy = FastMCP.as_proxy(backend={"rokbmcp": read_write_knowledge_base_mcp()})

    client: Client[FastMCPTransport] = Client(fastmcp)

    async with client:
        tools: list[Tool] = await client.list_tools()

    assert tools is not None
