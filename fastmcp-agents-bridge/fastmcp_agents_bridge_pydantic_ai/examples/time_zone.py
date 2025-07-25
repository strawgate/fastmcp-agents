from typing import TYPE_CHECKING, Any

import logfire
from fastmcp import FastMCP
from fastmcp.mcp_config import MCPConfig, TransformingStdioMCPServer
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.settings import ModelSettings

from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPToolset

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult

Agent.instrument_all()

logfire_config = logfire.configure(console=logfire.ConsoleOptions(min_log_level="info"), send_to_logfire=False)

model = GoogleModel("gemini-2.5-flash", provider=GoogleProvider(vertexai=True), settings=ModelSettings())

mcp_config = MCPConfig(
    mcpServers={
        "echo": TransformingStdioMCPServer(
            command="uvx",
            args=["mcp-server-time"],
            tools={},
        ),
    },
)

fastmcp_toolset: FastMCPToolset[None] = FastMCPToolset[None].from_mcp_config(mcp_config)

agent = Agent(
    "model",
    system_prompt="Be concise, reply with one sentence.",
    toolsets=[fastmcp_toolset],
)


class ConvertTimezonesResponse(BaseModel):
    provided_time: str
    converted_time: str
    starting_timezone: str
    ending_timezone: str


proxy: FastMCP[Any] = FastMCP[Any](name="time_zone")


@proxy.tool(name="convert_timezones")
async def convert_timezones(time: str, from_timezone: str, to_timezone: str) -> ConvertTimezonesResponse:
    """Convert a time from one timezone to another"""

    result: AgentRunResult[ConvertTimezonesResponse] = await agent.run(
        f"Convert {time} from {from_timezone} to {to_timezone}", output_type=ConvertTimezonesResponse
    )

    return result.output


if __name__ == "__main__":
    proxy.run(transport="sse")
