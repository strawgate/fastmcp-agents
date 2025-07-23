from pathlib import Path

from fastmcp import FastMCP
from fastmcp.tools.tool import Tool
from fastmcp_ai_agent_bridge.pydantic_ai import FastMCPToolset
from pydantic import AnyHttpUrl

from fastmcp_agents.library.agent.github.gather_background import GitHubIssueSummary, gather_background, gather_background_tool
from fastmcp_agents.library.agent.github.respond_to_issue import respond_to_issue
from fastmcp_agents.library.agent.simple_code.investigate import InvestigationResponse, investigate_code, investigate_code_tool

fastmcp = FastMCP[None](name="github-issue-triage")

fastmcp.add_tool(gather_background_tool)
fastmcp.add_tool(investigate_code_tool)

toolset = FastMCPToolset(fastmcp=fastmcp)


async def investigate_github_issue(
    *,
    owner: str,
    repo: str,
    reply_to_owner: str | None = None,
    reply_to_repo: str | None = None,
    reply_to_issue_number: int | None = None,
    code_path: Path | None = None,
    issue_number: int,
    reply_to_issue: bool,
) -> tuple[GitHubIssueSummary, InvestigationResponse, str | None]:
    issue_summary: GitHubIssueSummary = await gather_background(owner=owner, repo=repo, issue_number=issue_number)

    code_repository: Path | AnyHttpUrl

    if code_path:
        code_repository = code_path
    elif owner and repo:
        code_repository = AnyHttpUrl(f"https://github.com/{owner}/{repo}.git")
    else:
        msg = "Either code_path or owner and repo must be provided"
        raise ValueError(msg)

    investigation_response: InvestigationResponse = await investigate_code(
        task=issue_summary.detailed_summary,
        code_repository=code_repository,
    )

    if not reply_to_issue:
        return issue_summary, investigation_response, None

    response = await respond_to_issue(
        owner=reply_to_owner or owner,
        repo=reply_to_repo or repo,
        issue_number=reply_to_issue_number or issue_number,
        issue_summary=issue_summary,
        investigation=investigation_response,
    )

    return issue_summary, investigation_response, response


investigate_github_issue_tool = Tool.from_function(fn=investigate_github_issue)

fastmcp.add_tool(tool=investigate_github_issue_tool)

if __name__ == "__main__":
    fastmcp.run(transport="sse")
