from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastmcp import FastMCP
from fastmcp.mcp_config import MCPConfig, TransformingStdioMCPServer
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.toolsets import AbstractToolset

from fastmcp_agents.bridge.pydantic_ai.toolset import DynamicToolset, FastMCPServerToolset

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
    fastmcp_toolset: FastMCPServerToolset[None] = FastMCPServerToolset[None](server=proxy)

    agent = Agent(
        model,
        system_prompt="Be concise, reply with one sentence.",
        toolsets=[fastmcp_toolset],
    )

    result = await agent.run("What tools do you have available? Please test all of the tools to make sure they work.")
    print(result.output)


# async def test_agent_with_bridge_customize(model: GoogleModel):
#     mcp_config = MCPConfig(
#         mcpServers={
#             "echo": TransformingStdioMCPServer(
#                 command="uvx",
#                 args=["mcp-server-time"],
#                 tools={},
#             ),
#         },
#     )

#     async def prepare_mcp_config(ctx: RunContext[Path]) -> AbstractToolset[Path]:
#         return FastMCPServerToolset[Path].from_mcp_config(mcp_config=mcp_config)

#     dynamic_toolset: DynamicToolset[Path] = DynamicToolset[Path](build_toolset_fn=prepare_mcp_config)

#     agent = Agent[Path, str](
#         model,
#         system_prompt="Be concise, reply with one sentence.",
#         toolsets=[dynamic_toolset],
#         deps_type=Path,
#         output_type=str,
#     )

#     async with agent:
#         result = await agent.run(
#             deps=Path(), user_prompt="What tools do you have available? Please test all of the tools to make sure they work."
#         )
#         print(result.output)

#     async with agent:
#         result = await agent.run(
#             deps=Path(), user_prompt="What tools do you have available? Please test all of the tools to make sure they work."
#         )
#         print(result.output)
#     print(dynamic_toolset.toolset.toolsets)
