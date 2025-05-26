from __future__ import annotations

import asyncio
import logging
from logging import getLogger
from typing import Literal

import asyncclick as click
from fastmcp import Client, FastMCP
from fastmcp.utilities.logging import configure_logging
from rich.console import Console
from rich.logging import RichHandler

from fastmcp_agents.agent.base import FastMCPAgent
from fastmcp_agents.agent.llm_link.lltellm import AsyncLitellmLLMLink
from fastmcp_agents.agent.memory.ephemeral import EphemeralMemory
from fastmcp_agents.agent.observability.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("main")

mcp_config = {
    "Filesystem Operations": {
        "command": "uvx",
        "args": ["https://github.com/strawgate/mcp-many-files.git"],
    }
}

MCP_TRANSPORT_HELP = """
The transport to use for the MCP server.

- stdio: Use the standard input and output streams.
- sse: Use Server-Sent Events.
- streamable-http: Use the Streamable HTTP transport.
"""


@click.command()
@click.option(
    "--mcp-transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help=MCP_TRANSPORT_HELP,
)
async def cli(mcp_transport: Literal["stdio", "sse", "streamable-http"]):
    mcp_client = Client(mcp_config)

    configure_logging(level="DEBUG", logger=BASE_LOGGER.getChild("FastMCP"))

    async with mcp_client as client:
        server = FastMCP.as_proxy(client)

        tools = list((await server.get_tools()).values())

        remove_tools = [
            'call_tool_bulk', 'call_tools_bulk'
        ]

        filtered_tools = [tool for tool in tools if tool.name not in remove_tools]

    # web_agent = FastMCPAgent.from_model(
    #     name="Web Agent",
    #     description="A web agent that can fetch and scrape web pages.",
    #     system_prompt="You are a web agent that can fetch and scrape web pages.",
    #     model="vertexai/gemini-2.5-flash-05-20",
    # )

    # litellm uses "vertex_ai/gemini-2.5-flash-preview-05-20"
    # instructor uses "vertexai/gemini-2.5-flash-preview-05-20"

    web_agent = FastMCPAgent(
        name="Filesystem Agent",
        description="Assists with locating, categorizing, searching, reading, or writing files on the system.",
        default_instructions="""
        When you are asked to perform a task that requires you to interact with local files, 
        you should leverage the tools available to you to perform the task. If you are asked a
        question, you should leverage the tools available to you to answer the question.
        """,
        llm_link=AsyncLitellmLLMLink.from_model(
            model="vertex_ai/gemini-2.5-flash-preview-05-20",
        ),
        tools=filtered_tools,
        memory=EphemeralMemory(),
        tool_choice="required",
    )

    web_agent.register_as_tools(server)

    await server.run_async(transport=mcp_transport)


def run_mcp():
    asyncio.run(cli())


if __name__ == "__main__":
    run_mcp()
