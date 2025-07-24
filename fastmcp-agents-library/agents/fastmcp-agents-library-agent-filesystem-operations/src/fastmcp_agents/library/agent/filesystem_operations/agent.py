import os
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

from fastmcp import FastMCP
from fastmcp.tools.tool import Tool
from fastmcp_ai_agent_bridge.pydantic_ai import FastMCPToolset
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from fastmcp_agents.library.mcp.strawgate import (
    read_only_filesystem_mcp,
)

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult

read_only_filesystem_instructions = """
You have access to the Filesystem MCP server to read, search, and find files. When you get asked to complete
a task, you will use these tools to complete the task.
"""
read_write_filesystem_instructions = """
You have access to the Filesystem MCP server to write, create, delete, search, and find files. When you get asked to complete
a task, you will use these tools to complete the task.
"""

server = FastMCP[None](name="ask-filesystem-agent")


class FilesystemResponse(BaseModel):
    """The response from the ask_filesystem_agent."""

    response: str = Field(description="The response from the filesystem agent.")


ask_read_only_filesystem_agent = Agent(
    model=os.environ.get("MODEL"),
    instructions=dedent(
        text=f"""
        {read_only_filesystem_instructions}
        """
    ),
    output_type=FilesystemResponse,
)


async def ask_read_only_filesystem_agent_fn(directory: Path, question: str) -> FilesystemResponse:
    """Ask a question about the filesystem."""

    ro_filesystem_mcp = read_only_filesystem_mcp(root_dir=directory)
    filesystem_toolset = FastMCPToolset.from_mcp_config(mcp_config={"filesystem": ro_filesystem_mcp})

    async with ask_read_only_filesystem_agent:
        run_result: AgentRunResult[FilesystemResponse] = await ask_read_only_filesystem_agent.run(
            user_prompt=[question],
            toolsets=[filesystem_toolset],
        )

        return run_result.output


ask_read_only_filesystem_agent_tool = Tool.from_function(fn=ask_read_only_filesystem_agent_fn, name="ask_read_only_filesystem_agent")
server.add_tool(tool=ask_read_only_filesystem_agent_tool)


def run():
    """Run the agent."""
    server.run(transport="stdio")


if __name__ == "__main__":
    server.run(transport="sse")
