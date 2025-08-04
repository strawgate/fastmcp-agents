from pathlib import Path

from fastmcp.server import FastMCP
from fastmcp.tools import FunctionTool

from fastmcp_agents.library.agents.filesystem.agents import read_only_filesystem_agent, read_write_filesystem_agent
from fastmcp_agents.library.agents.shared.logging import configure_console_logging
from fastmcp_agents.library.agents.shared.models import Failure


async def investigate_filesystem(
    path: Path,
) -> str | Failure:
    """Investigate the code at the given path."""
    return (await read_only_filesystem_agent.run(deps=path)).output


read_only_filesystem_agent_tool = FunctionTool.from_function(fn=investigate_filesystem, name="filesystem_investigation_read_only")


async def perform_filesystem_task(
    path: Path,
) -> str | Failure:
    """Implement the code at the given path."""
    return (await read_write_filesystem_agent.run(deps=path)).output


filesystem_task_tool = FunctionTool.from_function(fn=perform_filesystem_task, name="filesystem_task")

server: FastMCP[None] = FastMCP[None](
    name="Filesystem Agent",
    tools=[
        read_only_filesystem_agent_tool,
        filesystem_task_tool,
    ],
)


def run():
    server.run()


def run_sse():
    configure_console_logging()
    server.run(transport="sse")


if __name__ == "__main__":
    run_sse()
