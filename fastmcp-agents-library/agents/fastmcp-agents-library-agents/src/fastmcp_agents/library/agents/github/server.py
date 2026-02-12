from typing import Annotated

from fastmcp.server import FastMCP
from fastmcp.tools import FunctionTool
from pydantic import Field

from fastmcp_agents.library.agents.github.agents.issue_driven_agent import (
    IssueDrivenAgentInput,
    IssueTriageAgentSettings,
    issue_driven_agent,
)
from fastmcp_agents.library.agents.github.dependencies.result import AgentResult
from fastmcp_agents.library.agents.shared.logging import configure_console_logging


async def triage_github_issue(
    issue_owner: Annotated[str, Field(description="The owner of the repository.")],
    issue_repo: Annotated[str, Field(description="The name of the repository.")],
    issue_number: Annotated[int, Field(description="The number of the issue.")],
    instructions: Annotated[str | None, Field(description="The instructions for the investigation.")] = None,
    settings: Annotated[IssueTriageAgentSettings | None, Field(description="The settings for the issue driven agent.")] = None,
) -> AgentResult:
    """Triage a GitHub issue, optionally restricting the investigation to a specific owner or repository."""

    if not settings:
        settings = IssueTriageAgentSettings()

    github_triage_input = IssueDrivenAgentInput(
        issue_owner=issue_owner, issue_repo=issue_repo, issue_number=issue_number, agent_settings=settings
    )

    return (await issue_driven_agent.run(deps=github_triage_input.to_deps(), user_prompt=instructions)).output


triage_github_issue_tool = FunctionTool.from_function(fn=triage_github_issue)

server: FastMCP[None] = FastMCP[None](
    name="GitHub",
    tools=[triage_github_issue_tool],
)


def run():
    configure_console_logging()
    server.run()


def run_http():
    configure_console_logging()
    server.run(transport="http")


if __name__ == "__main__":
    run_http()
