import pytest
from fastmcp.mcp_config import MCPConfig

from fastmcp_agents.library.mcp.modelcontextprotocol.git import git_mcp

from ..conftest import assert_mcp_init


@pytest.mark.asyncio
async def test_git_mcp_init():
    mcp_config: MCPConfig = MCPConfig(mcpServers={"gitmcp": git_mcp()})
    await assert_mcp_init(mcp_config=mcp_config)
