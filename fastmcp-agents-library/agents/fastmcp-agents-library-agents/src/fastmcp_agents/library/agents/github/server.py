from fastmcp.server import FastMCP
from fastmcp.tools import FunctionTool
from fastmcp_agents.library.agents.github.agents import github_triage_agent
from fastmcp_agents.library.agents.github.models import GitHubIssue, GitHubIssueSummary
from fastmcp_agents.library.agents.shared.logging import configure_console_logging
from fastmcp_agents.library.agents.shared.models import Failure


async def research_github_issue(
    investigate_issue_owner: str,
    investigate_issue_repo: str,
    investigate_issue_number: int,
    reply_to_issue_owner: str | None = None,
    reply_to_issue_repo: str | None = None,
    reply_to_issue_number: int | None = None,
) -> GitHubIssueSummary | Failure:
    """Research a GitHub issue, optionally restricting the investigation to a specific owner or repository.

    If `reply_to_issue` is provided, the investigation will be posted as a comment to the issue specified as the reply_to_issue. If you
    intend to do additional work based on the investigation, you should not have this tool reply to the issue.
    """
    if any([reply_to_issue_owner, reply_to_issue_repo, reply_to_issue_number]):  # noqa: SIM102
        if not all([reply_to_issue_owner, reply_to_issue_repo, reply_to_issue_number]):
            msg = "If you provide a reply_to_issue, you must provide all three of owner, repo, and issue_number"
            raise ValueError(msg)

    investigate_issue = GitHubIssue(
        owner=investigate_issue_owner,
        repo=investigate_issue_repo,
        issue_number=investigate_issue_number,
    )

    reply_to_issue: GitHubIssue | None = None

    if reply_to_issue_owner and reply_to_issue_repo and reply_to_issue_number:
        reply_to_issue = GitHubIssue(
            owner=reply_to_issue_owner,
            repo=reply_to_issue_repo,
            issue_number=reply_to_issue_number,
        )

    return (await github_triage_agent.run(deps=(investigate_issue, reply_to_issue))).output


research_github_issue_tool = FunctionTool.from_function(fn=research_github_issue)

server: FastMCP[None] = FastMCP[None](
    name="GitHub",
    tools=[research_github_issue_tool],
)


def run():
    server.run()


def run_http():
    server.run(transport="http")


if __name__ == "__main__":
    configure_console_logging()
    run_http()
