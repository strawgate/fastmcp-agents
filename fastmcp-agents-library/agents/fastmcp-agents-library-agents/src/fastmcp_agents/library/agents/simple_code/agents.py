#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform simple code tasks.
"""

import os
from typing import TYPE_CHECKING

from pydantic_ai.agent import Agent
from pydantic_ai.tools import RunContext

from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPServerToolset
from fastmcp_agents.library.agents.github.tools import git_diff
from fastmcp_agents.library.agents.shared.models import Failure
from fastmcp_agents.library.agents.simple_code.models import (
    BranchInfo,
    CodeAgentInput,
    CodeAgentResponse,
    DirectoryStructure,
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
    from pathlib import Path

    from fastmcp.mcp_config import TransformingStdioMCPServer


def report_completion(
    run_context: RunContext[CodeAgentInput],
    summary: str,
) -> CodeAgentResponse:
    code_base: Path = run_context.deps.code_base
    code_diff: str = git_diff(code_base=code_base)

    return CodeAgentResponse(summary=summary, code_diff=code_diff)


code_agent: Agent[CodeAgentInput, CodeAgentResponse | Failure] = Agent[CodeAgentInput, CodeAgentResponse | Failure](
    model=os.getenv("MODEL_CODE_IMPLEMENTATION_AGENT") or os.getenv("MODEL"),
    instructions=[
        WHO_YOU_ARE,
        YOUR_GOAL,
        GATHER_INFORMATION,
        COMPLETION_VERIFICATION,
        RESPONSE_FORMAT,
    ],
    deps_type=CodeAgentInput,
    output_type=[report_completion, Failure],
)


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


@code_agent.toolset(per_run_step=False)
async def filesystem_tools(ctx: RunContext[CodeAgentInput]) -> FastMCPServerToolset[CodeAgentInput]:  # pyright: ignore[reportUnusedParameter]
    path: Path = ctx.deps.code_base

    mcp_server: TransformingStdioMCPServer = (
        read_only_filesystem_mcp(root_dir=path)  # No Folding
        if ctx.deps.read_only
        else read_write_filesystem_mcp(root_dir=path)
    )

    return FastMCPServerToolset[CodeAgentInput].from_mcp_server(
        name="filesystem",
        mcp_server=mcp_server,
    )


@code_agent.toolset(per_run_step=False)
async def git_tools(ctx: RunContext[CodeAgentInput]) -> FastMCPServerToolset[CodeAgentInput]:  # pyright: ignore[reportUnusedParameter]  # noqa: ARG001
    git_mcp_server: TransformingStdioMCPServer = repo_path_restricted_git_mcp_server(
        repo_path=ctx.deps.code_base,
        repository=True,
        commit=True,
        branching=True,
        read_tools=True,
        write_tools=True,
    )

    return FastMCPServerToolset[CodeAgentInput].from_mcp_server(name="git", mcp_server=git_mcp_server)
