import json
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest

from fastmcp_agents.cli.main import app, call_tool, list_tools


@pytest.fixture
async def test_directory() -> AsyncGenerator[Path, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        config_json = Path(temp_dir) / "config.json"
        config_json.write_text(
            json.dumps({"mcpServers": {"filesystem": {"command": "uvx", "args": ["filesystem-operations-mcp", "--root-dir", temp_dir]}}})
        )

        subdir = Path(temp_dir) / "subdir"
        subdir.mkdir()

        random_file = subdir / "random_file.txt"
        random_file.write_text("Hello, world!")

        yield Path(temp_dir)


@pytest.mark.asyncio
async def test_app():
    assert app


@pytest.mark.asyncio
async def test_tool_call(test_directory: Path):
    result = await call_tool(config=test_directory / "config.json", tool="get_structure", args='{"depth": 3}')

    assert "subdir" in str(result.data)


async def test_list_tools(test_directory: Path):
    await list_tools(config=test_directory / "config.json")
