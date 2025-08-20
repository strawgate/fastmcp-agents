#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform simple code tasks.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from git.repo import Repo
from pydantic import Field
from pydantic_ai import ModelRetry
from pydantic_ai.agent import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.tools import RunContext, ToolDefinition

from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPServerToolset
from fastmcp_agents.library.agents.shared.models.status import Failure
from fastmcp_agents.library.agents.simple_code.models import (
    BranchInfo,
    CodeAgentInput,
    CodeAgentResponse,
    CodeChange,
    DirectoryStructure,
    InvestigationResult,
)
from fastmcp_agents.library.agents.simple_code.prompts import (
    COMPLETION_VERIFICATION,
    GATHER_INFORMATION,
    READ_ONLY_FILESYSTEM_TOOLS,
    READ_WRITE_FILESYSTEM_TOOLS,
    RESPONSE_FORMAT,
    WHO_YOU_ARE,
    YOUR_GOAL,
)
from fastmcp_agents.library.mcp.modelcontextprotocol.git import repo_path_restricted_git_mcp_server
from fastmcp_agents.library.mcp.strawgate.filesystem_operations import read_only_filesystem_mcp, read_write_filesystem_mcp

if TYPE_CHECKING:
    from fastmcp.mcp_config import TransformingStdioMCPServer


def git_diff(code_base: Path) -> str:
    """Get the diff of the code base."""
    repo = Repo(code_base)
    t = repo.head.commit.tree
    return repo.git.diff(t)


def git_check_uncommitted_changes(code_base: Path) -> bool:
    """Check if there are uncommitted changes in the code base."""
    repo = Repo(code_base)
    return repo.is_dirty()


def report_completion(
    run_context: RunContext[CodeAgentInput],
    summary: Annotated[
        str, Field(description="A summary of the changes made by the Agent that could be used as the body of a pull request.")
    ],
    code_changes: Annotated[list[CodeChange], Field(description="The code changes that were made by the Agent.")],
    allow_uncommitted_changes: Annotated[bool, Field(description="Whether to allow uncommitted changes to the code base.")],
) -> CodeAgentResponse:
    """Report the completion of the task.

    A full code diff is automatically included in the response so you do not need to describe the line-by-line changes but you
    should provide a detailed friendly description of the changes in `code_changes`.
    """
    code_base: Path = run_context.deps.code_base
    code_diff: str = git_diff(code_base=code_base)

    if not allow_uncommitted_changes and git_check_uncommitted_changes(code_base=code_base):
        raise ModelRetry(message="The code base is dirty. Did you remember to commit your changes before reporting completion?")

    return CodeAgentResponse(summary=summary, code_diff=code_diff, code_changes=code_changes)


async def force_agent_tools(ctx: RunContext[CodeAgentInput], tool_defs: list[ToolDefinition]) -> list[ToolDefinition] | None:
    """At certain steps, force the Agent to pick from a subset of the tools."""

    return tool_defs


model: GoogleModel = GoogleModel("gemini-2.5-flash")
settings: GoogleModelSettings = GoogleModelSettings(google_thinking_config={"include_thoughts": True})

code_agent: Agent[CodeAgentInput, CodeAgentResponse | Failure] = Agent[CodeAgentInput, CodeAgentResponse | Failure](
    model=os.getenv("MODEL_CODE_IMPLEMENTATION_AGENT") or os.getenv("MODEL"),
    instructions=[
        WHO_YOU_ARE,
        YOUR_GOAL,
        GATHER_INFORMATION,
        COMPLETION_VERIFICATION,
        RESPONSE_FORMAT,
    ],
    end_strategy="exhaustive",
    deps_type=CodeAgentInput,
    output_type=[report_completion, Failure],
    prepare_tools=force_agent_tools,
)


read_only_code_agent: Agent[CodeAgentInput, InvestigationResult | Failure] = Agent[CodeAgentInput, InvestigationResult | Failure](
    model=os.getenv("MODEL_CODE_IMPLEMENTATION_AGENT") or os.getenv("MODEL"),
    instructions=[
        WHO_YOU_ARE,
        YOUR_GOAL,
        GATHER_INFORMATION,
        (
            "You cannot make any changes to the code base. You can read the code base, find files, search etc, but you cannot make any, "
            "run any tests, make changes via git commands, or make any changes to the code base. Your goal is to investigate the code base "
            "and provide a detailed report of your findings following the instructions provided by the user."
        ),
        COMPLETION_VERIFICATION,
        RESPONSE_FORMAT,
    ],
    end_strategy="exhaustive",
    deps_type=CodeAgentInput,
    output_type=[InvestigationResult, Failure],
    prepare_tools=force_agent_tools,
)


@read_only_code_agent.instructions()
@code_agent.instructions()
async def filesystem_tool_instructions(ctx: RunContext[CodeAgentInput]) -> str:
    instructions = [READ_ONLY_FILESYSTEM_TOOLS]

    if branch_info := BranchInfo.from_dir(directory=ctx.deps.code_base):
        instructions.append(f"The Branch is: {branch_info.name} and the commit SHA is: {branch_info.commit_sha}.")

    if structure := DirectoryStructure.from_dir(directory=ctx.deps.code_base):
        instructions.append(f"The basic structure of the codebase is: {structure}.")

    if not ctx.deps.read_only:
        instructions.append(READ_WRITE_FILESYSTEM_TOOLS)

    return "\n".join(instructions)


@read_only_code_agent.toolset(per_run_step=False)
@code_agent.toolset(per_run_step=False)
async def filesystem_tools(ctx: RunContext[CodeAgentInput]) -> FastMCPServerToolset[CodeAgentInput]:  # pyright: ignore[reportUnusedParameter]
    path: Path = ctx.deps.code_base

    mcp_server: TransformingStdioMCPServer = (
        read_only_filesystem_mcp(root_dir=path)  # No Folding
        if ctx.deps.read_only
        else read_write_filesystem_mcp(root_dir=path, bulk_tools=True)
    )

    return FastMCPServerToolset[CodeAgentInput].from_mcp_server(
        name="filesystem",
        mcp_server=mcp_server,
    )


@read_only_code_agent.toolset(per_run_step=False)
@code_agent.toolset(per_run_step=False)
async def git_tools(ctx: RunContext[CodeAgentInput]) -> FastMCPServerToolset[CodeAgentInput]:  # pyright: ignore[reportUnusedParameter]
    git_mcp_server: TransformingStdioMCPServer = repo_path_restricted_git_mcp_server(
        repo_path=ctx.deps.code_base,
        repository=True,
        commit=True,
        branching=True,
        read_tools=True,
        write_tools=not ctx.deps.read_only,
    )

    return FastMCPServerToolset[CodeAgentInput].from_mcp_server(name="git", mcp_server=git_mcp_server)
