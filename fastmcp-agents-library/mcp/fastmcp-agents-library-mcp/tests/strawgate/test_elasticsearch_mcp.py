import os

import pytest
from fastmcp.mcp_config import MCPConfig

from fastmcp_agents.library.mcp.strawgate import elasticsearch_mcp
from tests.conftest import assert_mcp_init


@pytest.mark.asyncio
async def test_init():
    os.environ["ES_HOST"] = "http://localhost:9200"
    os.environ["ES_API_KEY"] = "changeme"
    mcp_config: MCPConfig = MCPConfig(mcpServers={"esmcp": elasticsearch_mcp()})
    await assert_mcp_init(mcp_config=mcp_config)
