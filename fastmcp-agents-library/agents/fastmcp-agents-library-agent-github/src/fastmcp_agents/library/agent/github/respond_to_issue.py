"""
This agent is used to triage issues on a GitHub repository.
"""

import os
from textwrap import dedent
from typing import Any

import yaml
from fastmcp import FastMCP
from fastmcp_ai_agent_bridge.pydantic_ai import FastMCPToolset
from pydantic_ai import Agent

from fastmcp_agents.library.agent.github.gather_background import GitHubIssueSummary
from fastmcp_agents.library.agent.github.shared.logging import configure_console_logging
from fastmcp_agents.library.agent.github.shared.prompts import (
    confidence_levels,
    issue_formatting_instructions,
    mindset_instructions,
    section_guidelines,
)
from fastmcp_agents.library.agent.simple_code.investigate import BranchInfo, InvestigationResponse
from fastmcp_agents.library.mcp.github import repo_restricted_github_mcp

configure_console_logging()

respond_instructions = f"""
## Persona & Goal:
You are a helpful assistant to an open source maintainer. You receive a bunch of background about an issue
and a triage performed by another maintainer and you reponse on the issue.

{mindset_instructions}
{confidence_levels}
{section_guidelines}
{issue_formatting_instructions}

Your response should include a summary + recommendations section alongside a very detailed findings section. All referenced
issues should be links and all code should be either 1) a permalink or 2) a code block.

Your goal is to reflect all of the details of the triage and background while producing a nicely formatted markdown response
in the GitHub comment. When you complete the task and report success include the body of the reponse of the comment.
"""


def mcp_servers_factory(owner: str, repo: str) -> dict[str, Any]:
    return {
        "github": repo_restricted_github_mcp(
            owner=owner,
            repo=repo,
            issues=True,
            pull_requests=False,
            discussions=False,
            repository=False,
        ),
    }


def repo_restricted_toolset_factory(owner: str, repo: str) -> FastMCPToolset:
    return FastMCPToolset.from_mcp_config(
        mcp_config=mcp_servers_factory(
            owner=owner,
            repo=repo,
        )
    )


issue_response_agent = Agent[Any, str](
    model=os.environ.get("MODEL"),
    system_prompt=respond_instructions,
    output_type=str,
)

server = FastMCP[None](name="respond-to-github-issue-background")


async def respond_to_issue(
    owner: str,
    repo: str,
    issue_number: int,
    issue_summary: GitHubIssueSummary,
    investigation: InvestigationResponse | None = None,
    branch_info: BranchInfo | None = None,
) -> str:
    background_yaml = yaml.safe_dump(issue_summary.model_dump())
    investigation_yaml = yaml.safe_dump(data=investigation.model_dump()) if investigation else None

    task = dedent(
        text=f"""The issue number to reply to is {issue_number}.

    The background information is as follows:
    {background_yaml}
    """
    ).strip()

    if investigation:
        task += dedent(
            text=f"""
        The investigation response is as follows:
        {investigation_yaml}
        """
        ).strip()

    if branch_info:
        task += dedent(
            text=f"""
        The investigation was performed against the {branch_info.name} branch on commit {branch_info.commit_sha}.
        """
        ).strip()

    run_result = await issue_response_agent.run(
        user_prompt=task, toolsets=[repo_restricted_toolset_factory(owner=owner, repo=repo)], output_type=str
    )

    print(run_result.output)

    return run_result.output
