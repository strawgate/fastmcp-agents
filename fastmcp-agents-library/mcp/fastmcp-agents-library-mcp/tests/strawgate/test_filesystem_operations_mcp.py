import pytest
from fastmcp.mcp_config import MCPConfig

from fastmcp_agents.library.mcp.strawgate import read_only_filesystem_mcp, read_write_filesystem_mcp
from tests.conftest import assert_mcp_init


@pytest.mark.asyncio
async def test_read_only_init():
    mcp_config: MCPConfig = MCPConfig(mcpServers={"fomcp": read_only_filesystem_mcp()})
    await assert_mcp_init(mcp_config=mcp_config)


@pytest.mark.asyncio
async def test_read_write_init():
    mcp_config: MCPConfig = MCPConfig(mcpServers={"fomcp": read_write_filesystem_mcp()})
    await assert_mcp_init(mcp_config=mcp_config)
