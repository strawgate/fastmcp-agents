#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform GitHub tasks.
"""

import os
from textwrap import dedent
from typing import TYPE_CHECKING

from pydantic_ai.agent import (
    Agent,
    RunContext,  # pyright: ignore[reportPrivateImportUsage]
)
from pydantic_ai.tools import ToolDefinition

from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPServerToolset
from fastmcp_agents.library.agents.github.models import (
    GitHubIssue,
    IssueDrivenAgentInput,
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
from fastmcp_agents.library.agents.github.tools import (
    create_initial_comment,
    get_issue,
    get_issue_comments,
    progress_update_toolset,
    report_completion,
    report_failure,
)
from fastmcp_agents.library.agents.shared.models import Failure
from fastmcp_agents.library.agents.simple_code.agents import code_agent
from fastmcp_agents.library.agents.simple_code.models import CodeAgentInput, CodeAgentResponse
from fastmcp_agents.library.mcp.github import (
    repo_restrict_github_mcp,
)

if TYPE_CHECKING:
    from fastmcp.mcp_config import TransformingStdioMCPServer

InvestigateIssue = GitHubIssue
ReplyToIssue = GitHubIssue
ReplyWithPullRequest = bool

PLANNING_INTERVAL = 5

async def force_agent_tools(ctx: RunContext[IssueDrivenAgentInput], tool_defs: list[ToolDefinition]) -> list[ToolDefinition] | None:
    """At certain steps, force the Agent to pick from a subset of the tools."""

    keep_tools: list[str] = []

    if ctx.run_step == 0:
        comment_id = create_initial_comment(
            owner=ctx.deps.investigate_issue.owner,
            repo=ctx.deps.investigate_issue.repo,
            issue_number=ctx.deps.investigate_issue.issue_number,
            new_comment="Starting investigation of issue. I will update this comment as I work on the issue!",
        )
        ctx.deps.comment_id = comment_id

    if ctx.run_step in {0, 1}:
        keep_tools.extend(["add_to_checklist"])

    elif ctx.run_step >= PLANNING_INTERVAL and ctx.run_step % PLANNING_INTERVAL == 0:
        keep_tools.extend(
            [
                "report_progress",
                "report_issue_encountered",
                "add_to_checklist",
                "check_off_items",
                "add_related_issue",
                "add_related_file",
            ]
        )

    return [tool_def for tool_def in tool_defs if tool_def.name in keep_tools] if keep_tools else tool_defs



issue_driven_agent: Agent[IssueDrivenAgentInput, str | Failure] = Agent[IssueDrivenAgentInput, str | Failure](
    name="issue-driven-agent",
    model=os.getenv("MODEL_ISSUE_DRIVEN_AGENT") or os.getenv("MODEL"),
    instructions=[
        WHO_YOU_ARE,
        YOUR_GOAL,
        YOUR_MINDSET,
        GATHER_INSTRUCTIONS,
        REPORTING_CONFIDENCE,
        INVESTIGATION_INSTRUCTIONS,
        RESPONSE_FORMAT,
    ],
    toolsets=[progress_update_toolset],
    prepare_tools=force_agent_tools,
    deps_type=IssueDrivenAgentInput,
    output_type=[report_completion, report_failure],
)


@issue_driven_agent.instructions
async def issue_driven_agent_instructions(
    ctx: RunContext[IssueDrivenAgentInput],
) -> str:
    github_issue: GitHubIssue = ctx.deps.investigate_issue

    issue_body = get_issue(owner=github_issue.owner, repo=github_issue.repo, issue_number=github_issue.issue_number)
    issue_comments = get_issue_comments(owner=github_issue.owner, repo=github_issue.repo, issue_number=github_issue.issue_number)

    formatted_issue_comments = "\n\n".join(
        [
            f"**{comment.user.role_name} {comment.user.login} at {comment.created_at.strftime('%Y-%m-%d %H:%M:%S')}**\n{comment.body}"
            for comment in issue_comments
        ]
    )

    return dedent(
        text=f"""The issue for this task is:
    {github_issue.owner}/{github_issue.repo}#{github_issue.issue_number}

    The issue body is:
    ``````````````````````
    {issue_body.body}
    ``````````````````````

    The issue comments are:
    ``````````````````````
    {formatted_issue_comments}
    ``````````````````````
    """
    )


@issue_driven_agent.toolset(per_run_step=False)
async def restricted_github_toolset(
    ctx: RunContext[IssueDrivenAgentInput],
) -> FastMCPServerToolset[IssueDrivenAgentInput]:
    issue_driven_agent_input: IssueDrivenAgentInput = ctx.deps
    investigate_issue: GitHubIssue = issue_driven_agent_input.investigate_issue

    github_mcp_server: TransformingStdioMCPServer = repo_restrict_github_mcp(
        owner=investigate_issue.owner,
        repo=investigate_issue.repo,
        issues=True,
        pull_requests=True,
        discussions=True,
        repository=True,
        read_tools=True,
        write_tools=False,
    )

    return FastMCPServerToolset[IssueDrivenAgentInput].from_mcp_server(name="github", mcp_server=github_mcp_server)


@issue_driven_agent.tool()
async def handoff_to_code_agent(ctx: RunContext[IssueDrivenAgentInput]) -> CodeAgentResponse | Failure:
    """Handoff to the code agent."""

    code_agent_input = CodeAgentInput(
        code_base=ctx.deps.options.code_base,
        read_only=False,
    )

    return (
        await code_agent.run(
            user_prompt="",
            deps=code_agent_input,
            message_history=ctx.messages,
        )
    ).output
