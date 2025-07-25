from typing import TYPE_CHECKING

import pytest
from fastmcp import FastMCP
from fastmcp.mcp_config import MCPConfig, TransformingStdioMCPServer
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPToolset

if TYPE_CHECKING:
    from fastmcp.server.proxy import FastMCPProxy


@pytest.fixture
def gemini_provider() -> GoogleProvider:
    return GoogleProvider(vertexai=False)


@pytest.fixture
def model(gemini_provider: GoogleProvider) -> GoogleModel:
    return GoogleModel("gemini-2.5-flash", provider=gemini_provider)


@pytest.mark.asyncio
async def test_agent(model: GoogleModel):
    agent = Agent(
        model,
        system_prompt="Be concise, reply with one sentence.",
    )

    result = await agent.run('Where does "hello world" come from?')

    assert result.output is not None


async def test_agent_with_bridge(model: GoogleModel):
    mcp_config = MCPConfig(
        mcpServers={
            "echo": TransformingStdioMCPServer(
                command="uvx",
                args=["mcp-server-time"],
                tools={},
            ),
        },
    )

    proxy: FastMCPProxy = FastMCP.as_proxy(backend=mcp_config)
    fastmcp_toolset: FastMCPToolset[None] = FastMCPToolset[None](fastmcp=proxy)

    agent = Agent(
        model,
        system_prompt="Be concise, reply with one sentence.",
        toolsets=[fastmcp_toolset],
    )

    result = await agent.run("What tools do you have available? Please test all of the tools to make sure they work.")
    print(result.output)
