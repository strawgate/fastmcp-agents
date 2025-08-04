from pathlib import Path

from fastmcp.server import FastMCP
from fastmcp.tools import FunctionTool
from fastmcp_agents.library.agents.shared.logging import configure_console_logging
from fastmcp_agents.library.agents.shared.models import Failure
from fastmcp_agents.library.agents.simple_code.agents import code_implementation_agent, code_investigation_agent
from fastmcp_agents.library.agents.simple_code.models import ImplementationResponse, InvestigationResult


async def investigate_code(
    path: Path,
) -> InvestigationResult | Failure:
    """Investigate the code at the given path."""
    return (await code_investigation_agent.run(deps=path)).output


code_investigation_agent_tool = FunctionTool.from_function(fn=investigate_code, name="code_investigation_agent")


async def implement_code(
    path: Path,
) -> ImplementationResponse | Failure:
    """Implement the code at the given path."""
    return (await code_implementation_agent.run(deps=path)).output


code_agent_tool = FunctionTool.from_function(fn=implement_code, name="code_agent")

server: FastMCP[None] = FastMCP[None](
    name="Code Agent",
    tools=[
        code_investigation_agent_tool,
        code_agent_tool,
    ],
)


def run():
    server.run()


def run_sse():
    configure_console_logging()
    server.run(transport="sse")


if __name__ == "__main__":
    run_sse()
