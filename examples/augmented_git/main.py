from __future__ import annotations

import asyncio
import logging
from logging import getLogger
from typing import Literal

import asyncclick as click
from fastmcp import Client, FastMCP
from fastmcp.utilities.logging import configure_logging

from fastmcp_agents.agent.base import FastMCPAgent
from fastmcp_agents.agent.llm_link.lltellm import AsyncLitellmLLMLink
from fastmcp_agents.agent.memory.ephemeral import EphemeralMemory
from fastmcp_agents.agent.observability.logging import BASE_LOGGER

mcp_config = {
    "git-server": {
        "command": "uvx",
        "args": ["git+https://github.com/modelcontextprotocol/servers.git#subdirectory=src/git"],
    }
}

MCP_TRANSPORT_HELP = """
The transport to use for the MCP server.

- stdio: Use the standard input and output streams.
- sse: Use Server-Sent Events.
- streamable-http: Use the Streamable HTTP transport.
"""


@click.command(allow_extra_args=True)
@click.option(
    "--mcp-transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help=MCP_TRANSPORT_HELP,
)
@click.option("--remove-tool", type=str, multiple=True, help="The name of the tool to remove from the agent.")
async def cli(mcp_transport: Literal["stdio", "sse", "streamable-http"], *args, remove_tool: list[str]):
    mcp_config["git-server"]["args"] = list(mcp_config["git-server"]["args"]) + list(args)

    mcp_client = Client(mcp_config)

    configure_logging(level="INFO", logger=BASE_LOGGER.getChild("FastMCP"))

    async with mcp_client as client:
        server = FastMCP.as_proxy(client)

        tools = list((await server.get_tools()).values())

        remove_tools = remove_tool or []

        filtered_tools = [tool for tool in tools if tool.name not in remove_tools]

        llm_link=AsyncLitellmLLMLink.from_model(
            model="vertex_ai/gemini-2.5-flash-preview-05-20",
        )
        web_agent = FastMCPAgent(
            name="Git Agent",
            description="Assists with performing Git operations as requested by the user.",
            default_instructions="""
            When you are asked to perform a task that requires you to interact with local files, 
            you should leverage the tools available to you to perform the task. If you are asked a
            question, you should leverage the tools available to you to answer the question.
            """,
            tools=filtered_tools,
            llm_link=llm_link,
        )

        web_agent.register_as_tools(server)

        await server.run_async(transport=mcp_transport)


def run_mcp():
    asyncio.run(cli())


if __name__ == "__main__":
    run_mcp()
