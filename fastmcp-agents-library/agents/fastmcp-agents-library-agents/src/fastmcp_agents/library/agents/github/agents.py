#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform GitHub tasks.
"""

import os
from pathlib import Path

from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig
from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPServerToolset
from fastmcp_agents.library.agents.github.models import (
    GitHubIssue,
    GitHubIssueSummary,
)
from fastmcp_agents.library.agents.github.prompts import (
    GATHER_INSTRUCTIONS,
    INVESTIGATION_INSTRUCTIONS,
    REPORTING_CONFIDENCE,
    RESPONSE_FORMAT,
    WHO_YOU_ARE,
    YOUR_GOAL,
    YOUR_MINDSET,
)
from fastmcp_agents.library.agents.shared.models import Failure
from fastmcp_agents.library.agents.simple_code.agents import code_investigation_agent
from fastmcp_agents.library.mcp.github import (
    repo_restrict_github_mcp,
)
from fastmcp_agents.library.mcp.github.github import REPLY_ISSUE_TOOLS
from git.repo import Repo
from gitdb.db.loose import tempfile
from pydantic_ai.agent import (
    Agent,
    RunContext,  # pyright: ignore[reportPrivateImportUsage]
)

InvestigateIssue = GitHubIssue
ReplyToIssue = GitHubIssue


def research_github_issue_instructions(ctx: RunContext[tuple[InvestigateIssue, ReplyToIssue | None]]) -> str:  # pyright: ignore[reportUnusedFunction]
    issue: GitHubIssue = ctx.deps[0]
    return f"""Gather context about GitHub issue {issue.issue_number} in {issue.owner}/{issue.repo}."""



github_triage_agent = Agent[tuple[InvestigateIssue, ReplyToIssue | None], GitHubIssueSummary | Failure](
    model=os.getenv("MODEL_RESEARCH_GITHUB_ISSUE") or os.getenv("MODEL"),
    system_prompt=[
        WHO_YOU_ARE,
        YOUR_GOAL,
        YOUR_MINDSET,
    ],
    instructions=[
        GATHER_INSTRUCTIONS,
        REPORTING_CONFIDENCE,
        research_github_issue_instructions,
        INVESTIGATION_INSTRUCTIONS,
        RESPONSE_FORMAT,
    ],
    deps_type=tuple[InvestigateIssue, ReplyToIssue | None],
    output_type=[GitHubIssueSummary, Failure],
)

@github_triage_agent.toolset(per_run_step=False)
async def github_triage_toolset(
    ctx: RunContext[tuple[InvestigateIssue, ReplyToIssue | None]],
) -> FastMCPServerToolset[tuple[InvestigateIssue, ReplyToIssue | None]]:
    investigate_issue, reply_to_issue = ctx.deps

    github_mcp_server = repo_restrict_github_mcp(
        owner=investigate_issue.owner,
        repo=investigate_issue.repo,
        issues=True,
        pull_requests=True,
        discussions=True,
        repository=True,
        read_tools=True,
        write_tools=False,
    )

    if reply_to_issue:
        for tool_name in REPLY_ISSUE_TOOLS:
            github_mcp_server.tools[tool_name] = ToolTransformConfig(
                arguments={
                    "owner": ArgTransformConfig(default=reply_to_issue.owner, hide=True),
                    "repo": ArgTransformConfig(default=reply_to_issue.repo, hide=True),
                    "issue_number": ArgTransformConfig(default=reply_to_issue.issue_number, hide=True),
                },
                tags=github_mcp_server.include_tags or set(),
            )

    return FastMCPServerToolset[tuple[InvestigateIssue, ReplyToIssue | None]].from_mcp_server(name="github", mcp_server=github_mcp_server)


@github_triage_agent.tool
async def investigate_code_base(ctx: RunContext[tuple[InvestigateIssue, ReplyToIssue | None]], task: str):  # pyright: ignore[reportUnusedFunction]
    """Investigate the code base of the repository in relation to the issue."""

    with tempfile.TemporaryDirectory() as temp_dir:
        clone: Repo = Repo.clone_from(url=str(ctx.deps[0].repository_git_url()), to_path=temp_dir, depth=1, single_branch=True)
        clone_path: Path = Path(clone.working_dir)

        # Invoke the Code Agent, passing in the message history from the research agent
        return (
            await code_investigation_agent.run(
                user_prompt=task,
                message_history=ctx.messages,
                deps=clone_path,
            )
        ).output
