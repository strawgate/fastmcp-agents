#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform GitHub tasks.
"""

import os
from collections.abc import Sequence
from typing import Any

import yaml
from fastmcp import FastMCP
from fastmcp.tools import Tool
from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPToolset
from fastmcp_agents.library.agents.github.models import GitHubIssueSummary
from fastmcp_agents.library.agents.github.prompts import (
    REPORTING_CONFIDENCE,
    RESPONSE_FORMAT,
    WHO_YOU_ARE,
    YOUR_GOAL,
    YOUR_MINDSET,
)
from fastmcp_agents.library.mcp.github.github import repo_restricted_github_mcp
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult

gather_background_agent = Agent(
    model=os.getenv("MODEL"),
    system_prompt=WHO_YOU_ARE
    + YOUR_GOAL
    + YOUR_MINDSET
    + """You will perform multiple searches against the repository across issues, pull requests, and discussions to identify
and relevant information for the issue. If you find a relevant related item, you will review the comments or discussion
under that item to determine if it is related to the issue and how it might be related.

Your goal is to "connect the dots", and gather all related information to assist the maintainer in investigating the issue."""
    + REPORTING_CONFIDENCE
    + RESPONSE_FORMAT,
)


async def gather_github_issue_background_raw(owner: str, repo: str, issue_number: int) -> AgentRunResult[GitHubIssueSummary]:
    """Perform a read-only investigation of the codebase. Returning the raw Agent Run Result."""

    toolset: FastMCPToolset[Any] = FastMCPToolset.from_mcp_server(
        name="github",
        mcp_server=repo_restricted_github_mcp(owner=owner, repo=repo, read_only=True),
    )

    async with gather_background_agent as agent:
        return await agent.run(
            user_prompt=f"The issue number to gather background information for is {issue_number}.",
            toolsets=[toolset],
            output_type=GitHubIssueSummary,
        )


async def gather_github_issue_background(owner: str, repo: str, issue_number: int) -> GitHubIssueSummary:
    return (await gather_github_issue_background_raw(owner=owner, repo=repo, issue_number=issue_number)).output


gather_background_tool = Tool.from_function(fn=gather_github_issue_background)


issue_response_agent = Agent[Any, str](
    model=os.environ.get("MODEL"),
    system_prompt=WHO_YOU_ARE
    + YOUR_GOAL
    + YOUR_MINDSET
    + REPORTING_CONFIDENCE
    + """Your response should include a summary + recommendations section alongside a very detailed findings section. All referenced
issues should be links and all code should be either 1) a permalink or 2) a code block.

Your goal is to reflect all of the details of the triage and background while producing a nicely formatted markdown response
in the GitHub comment. When you complete the task and report success include the body of the reponse of the comment."""
    + RESPONSE_FORMAT,
    output_type=str,
)


async def comment_on_github_issue_raw(owner: str, repo: str, issue_number: int, information: Sequence[BaseModel]) -> AgentRunResult[str]:
    toolset: FastMCPToolset[Any] = FastMCPToolset.from_mcp_server(
        name="github",
        mcp_server=repo_restricted_github_mcp(
            owner=owner,
            repo=repo,
            read_only=False,
            issues=True,
            pull_requests=False,
            discussions=False,
            repository=False,
        ),
    )

    async with issue_response_agent as agent:
        task = f"We have gathered the following information related to issue {issue_number} and it's time to formulate a reply:"
        for model in information:
            task += f"\n\n{yaml.safe_dump(model.model_dump(), indent=2)}"
        return await agent.run(user_prompt=task, toolsets=[toolset], output_type=str)


async def comment_on_github_issue(owner: str, repo: str, issue_number: int, information: Sequence[BaseModel]) -> str:
    return (await comment_on_github_issue_raw(owner=owner, repo=repo, issue_number=issue_number, information=information)).output


comment_on_github_issue_tool = Tool.from_function(fn=comment_on_github_issue)

server = FastMCP[None](name="github-issue-triage", tools=[gather_background_tool, comment_on_github_issue_tool])


def run():
    server.run()


def run_sse():
    server.run(transport="sse")
