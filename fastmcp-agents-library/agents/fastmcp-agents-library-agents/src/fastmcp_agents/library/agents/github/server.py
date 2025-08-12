from typing import Annotated

from fastmcp.server import FastMCP
from fastmcp.tools import FunctionTool
from pydantic import Field

from fastmcp_agents.library.agents.github.agents import issue_driven_agent
from fastmcp_agents.library.agents.github.models import GitHubIssue, IssueDrivenAgentInput, IssueDrivenAgentOptions
from fastmcp_agents.library.agents.shared.logging import configure_console_logging
from fastmcp_agents.library.agents.shared.models import Failure


async def triage_github_issue(
    issue_owner: Annotated[str, Field(description="The owner of the repository.")],
    issue_repo: Annotated[str, Field(description="The name of the repository.")],
    issue_number: Annotated[int, Field(description="The number of the issue.")],
    instructions: Annotated[str | None, Field(description="The instructions for the investigation.")] = None,
) -> str | Failure:
    """Triage a GitHub issue, optionally restricting the investigation to a specific owner or repository.

    If `reply_to_issue` is provided, the investigation will be posted as a comment to the issue specified as the reply_to_issue. If you
    intend to do additional work based on the investigation, you should not have this tool reply to the issue.
    """

    github_triage_input = IssueDrivenAgentInput(
        investigate_issue=GitHubIssue(
            owner=issue_owner,
            repo=issue_repo,
            issue_number=issue_number,
        ),
        options=IssueDrivenAgentOptions(),
    )

    return (await issue_driven_agent.run(deps=github_triage_input, user_prompt=instructions)).output


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
