"""
This agent is used to triage issues on a GitHub repository.
"""

import os
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.tools.tool import Tool
from fastmcp_ai_agent_bridge.pydantic_ai import FastMCPToolset
from pydantic import BaseModel
from pydantic_ai import Agent

from fastmcp_agents.library.agent.github.shared.logging import configure_console_logging
from fastmcp_agents.library.agent.github.shared.prompts import (
    confidence_levels,
    mindset_instructions,
    section_guidelines,
)
from fastmcp_agents.library.mcp.github import repo_restricted_github_mcp
from fastmcp_agents.library.mcp.nickclyde import duckduckgo_mcp

configure_console_logging()

gather_background_instructions = f"""
## Persona & Goal:
You are a helpful assistant to an open source maintainer. You triage issues posted on a GitHub repository, looking
to connect them with previous issues posted, open or closed pull requests, and discussions.

{mindset_instructions}
{confidence_levels}
{section_guidelines}

You will perform multiple searches against the repository across issues, pull requests, and discussions to identify
and relevant information for the issue. If you find a relevant related item, you will review the comments or discussion
under that item to determine if it is related to the issue and how it might be related.

Your goal is to "connect the dots", and gather all related information to assist the maintainer in investigating the issue.
"""


def mcp_servers_factory(owner: str, repo: str) -> dict[str, Any]:
    return {
        "duckduckgo": duckduckgo_mcp(),
        "github": repo_restricted_github_mcp(owner=owner, repo=repo, read_only=True),
    }


def repo_restricted_toolset_factory(owner: str, repo: str) -> FastMCPToolset:
    return FastMCPToolset.from_mcp_config(
        mcp_config=mcp_servers_factory(
            owner=owner,
            repo=repo,
        )
    )


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


gather_background_agent = Agent[Any, GitHubIssueSummary](
    model=os.environ.get("MODEL"),
    system_prompt=gather_background_instructions,
    output_type=GitHubIssueSummary,
)

server = FastMCP[None](name="gather-github-issue-background")


async def gather_background(owner: str, repo: str, issue_number: int) -> GitHubIssueSummary:
    result = await gather_background_agent.run(
        user_prompt=[
            f"The issue number to gather background information for is {issue_number}.",
        ],
        toolsets=[repo_restricted_toolset_factory(owner=owner, repo=repo)],
    )

    return result.output


gather_background_tool = Tool.from_function(fn=gather_background)

server.add_tool(tool=gather_background_tool)


def run():
    server.run()


if __name__ == "__main__":
    server.run(transport="sse")
