"""
This agent is used to triage issues on a GitHub repository.
"""

from typing import TYPE_CHECKING, Any, Literal, override

from pydantic import BaseModel, Field

from fastmcp_agents.core.agents.base import DefaultFailureModel
from fastmcp_agents.core.agents.task import TaskAgent
from fastmcp_agents.core.models.server_builder import FastMCPAgents
from fastmcp_agents.library.agent.github.shared.helpers import (
    generate_background,
    get_issue_background,
    restricted_get_issue_tool_factory,
    restricted_get_pull_request_tool_factory,
    restricted_search_issues_tool_factory,
)
from fastmcp_agents.library.agent.github.shared.mcp import github_mcp_server
from fastmcp_agents.library.agent.simple_code.investigate import CodeInvestigationAgent

if TYPE_CHECKING:
    from fastmcp.tools.tool import Tool as FastMCPTool

gather_background_instructions = """
## Persona & Goal:
You are a helpful assistant to an open source maintainer. You triage issues posted on a GitHub repository, looking
to connect them with previous issues posted, open or closed pull requests, and discussions.

{mindset_instructions}
{confidence_levels}
{section_guidelines}

Your goal is to "connect the dots", and gather all related information to assist the maintainer in investigating the issue.
"""


mcp_servers = {
    "github": github_mcp_server,
}


class GitHubRelatedIssue(BaseModel):
    issue_title: str
    issue_number: int
    confidence: Literal["high", "medium", "low"]
    reason: str


class GitHubIssueSummary(BaseModel):
    issue_title: str
    issue_number: int
    detailed_summary: str
    related_issues: list[GitHubRelatedIssue]


class GitHubIssueBackgroundAgent(TaskAgent):
    """An agent that can gather background information about a GitHub issue."""

    name: str = "ask_issue_background"

    mcp: dict[str, Any] = Field(default=mcp_servers)

    instructions: str = gather_background_instructions

    @override
    async def __call__(
        self,
        *,
        issue_repository_owner: str,
        issue_repository: str,
        issue_number: int,
        code_repository_owner: str | None = None,
        code_repository: str | None = None,
    ) -> GitHubIssueSummary | DefaultFailureModel:
        """Gather background information about a GitHub issue."""

        if code_repository_owner is None or code_repository is None:
            code_repository_owner = issue_repository_owner
            code_repository = issue_repository

        tools: dict[str, FastMCPTool] = await self.get_tools()

        restricted_tools: dict[str, FastMCPTool] = {
            "get_issue": await restricted_get_issue_tool_factory(tools, issue_repository_owner, issue_repository),
            "get_pull_request": await restricted_get_pull_request_tool_factory(tools, issue_repository_owner, issue_repository),
            "search_issues": await restricted_search_issues_tool_factory(issue_repository_owner, issue_repository),
        }

        issue_content, comments_content = await get_issue_background(tools, issue_repository_owner, issue_repository, issue_number)

        background = generate_background(
            issue_content, comments_content, "It is mandatory to use the Code Investigation Agent to investigate the code repository."
        )

        code_investigation_agent = CodeInvestigationAgent(tools_from_context=self.tools_from_context)

        restricted_tools["code_investigation"] = code_investigation_agent.to_tool()

        return await self.handle_task(task=background, tools=restricted_tools, success_model=GitHubIssueSummary)


server = FastMCPAgents(
    name="gather-github-issue-background",
    mcp=mcp_servers,
    agents=[GitHubIssueBackgroundAgent(tools_from_context=True)],
).to_server()


if __name__ == "__main__":
    server.run(transport="sse")
