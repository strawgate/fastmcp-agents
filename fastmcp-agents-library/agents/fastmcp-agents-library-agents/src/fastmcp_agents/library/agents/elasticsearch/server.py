from fastmcp.server import FastMCP
from fastmcp.tools import FunctionTool

from fastmcp_agents.library.agents.elasticsearch.agents import ask_esql_expert
from fastmcp_agents.library.agents.elasticsearch.models import AskESQLExpertResponse
from fastmcp_agents.library.agents.shared.logging import configure_console_logging


async def ask_esql_expert_fn(
    question: str,
) -> AskESQLExpertResponse:
    """Ask an ESQL question."""
    return (await ask_esql_expert.run(user_prompt=question)).output


ask_esql_expert_tool = FunctionTool.from_function(fn=ask_esql_expert_fn, name="ask_esql_expert")


server: FastMCP[None] = FastMCP[None](
    name="ESQL Expert",
    tools=[
        ask_esql_expert_tool,
    ],
)


def run():
    server.run()


def run_sse():
    configure_console_logging()
    server.run(transport="sse")


if __name__ == "__main__":
    run_sse()
