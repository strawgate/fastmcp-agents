
from pathlib import Path

import pytest

from fastmcp_agents.cli.main import app, call_tool, list_tools


@pytest.mark.asyncio
async def test_app():
    assert app

@pytest.mark.asyncio
async def test_tool_call():
    result = await call_tool(config=Path("config.json"), tool="get_structure", args='{"depth": 3}')

    assert "src/fastmcp_agents/cli" in str(result.data)

async def test_list_tools():
    await list_tools(config=Path("config.json"))
