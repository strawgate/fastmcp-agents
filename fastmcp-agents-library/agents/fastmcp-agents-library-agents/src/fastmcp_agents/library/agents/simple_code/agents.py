#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform simple code tasks.
"""

import os
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPToolset
from fastmcp_agents.library.agents.simple_code.models import BranchInfo, DirectoryStructure, ImplementationResponse, InvestigationResult
from fastmcp_agents.library.agents.simple_code.prompts import (
    COMPLETION_VERIFICATION,
    GATHER_INFORMATION,
    READ_ONLY_FILESYSTEM_TOOLS,
    READ_WRITE_FILESYSTEM_TOOLS,
    RESPONSE_FORMAT,
    WHO_YOU_ARE,
    YOUR_GOAL,
)
from fastmcp_agents.library.mcp.strawgate.filesystem_operations import read_only_filesystem_mcp, read_write_filesystem_mcp
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.tools import RunContext

code_investigation_agent = Agent[Path](
    model=os.getenv("MODEL"),
    system_prompt=WHO_YOU_ARE
    + YOUR_GOAL
    + GATHER_INFORMATION
    + READ_ONLY_FILESYSTEM_TOOLS
    + "You yourself cannot change the codebase, so any changes you present will be proposed changes to the codebase."
    + COMPLETION_VERIFICATION
    + RESPONSE_FORMAT,
    deps_type=Path,
)

code_implementation_agent = Agent[Path](
    model=os.getenv("MODEL"),
    system_prompt=WHO_YOU_ARE
    + YOUR_GOAL
    + GATHER_INFORMATION
    + READ_ONLY_FILESYSTEM_TOOLS
    + READ_WRITE_FILESYSTEM_TOOLS
    + COMPLETION_VERIFICATION
    + RESPONSE_FORMAT,
    deps_type=Path,
)

# code_review_agent = Agent[Path](
#     model=os.getenv("MODEL"),
#     system_prompt=WHO_YOU_ARE
#     + YOUR_GOAL
#     + GATHER_INFORMATION
#     + READ_ONLY_FILESYSTEM_TOOLS
#     + """You are provided the results of a code investigation from a junior engineer and the code base. It is your job to review
#     the investigation and affirm that it represents the most plausible explanation for the issue or question."""
#     + RESPONSE_FORMAT,
#     deps_type=Path,
# )


@code_investigation_agent.instructions()
@code_implementation_agent.instructions()
def add_repo_structure(ctx: RunContext[Path]) -> str:
    structure: DirectoryStructure = DirectoryStructure.from_dir(directory=ctx.deps)
    return f"The basic structure of the codebase is: {structure}."


@code_investigation_agent.instructions()
@code_implementation_agent.instructions()
def add_branch_info(ctx: RunContext[Path]) -> str:
    branch_info: BranchInfo | None = BranchInfo.from_dir(directory=ctx.deps)
    if branch_info is None:
        return "Could not determine the Git branch information."

    return f"The Branch is: {branch_info.name} and the commit SHA is: {branch_info.commit_sha}."


async def investigate_code_repository_raw(task: str, code_repository: Path) -> AgentRunResult[InvestigationResult]:
    """Perform a read-only investigation of the codebase. Returning the raw Agent Run Result."""

    toolset: FastMCPToolset[Any] = FastMCPToolset.from_mcp_server(
        name="filesystem",
        mcp_server=read_only_filesystem_mcp(root_dir=code_repository),
    )

    async with code_investigation_agent as agent:
        return await agent.run(
            user_prompt=task,
            deps=code_repository,
            toolsets=[toolset],
            output_type=InvestigationResult,
        )


async def investigate_code_repository(task: str, code_repository: Path) -> InvestigationResult:
    """Perform a read-only investigation of the codebase following the prompt provided in `task`."""
    return (await investigate_code_repository_raw(task, code_repository)).output


investigate_code_repository_tool = FunctionTool.from_function(fn=investigate_code_repository)


async def implement_code_change_raw(task: str, code_repository: Path) -> AgentRunResult[ImplementationResponse]:
    """Implement the code following the prompt provided in `task`."""

    toolset: FastMCPToolset[Any] = FastMCPToolset.from_mcp_server(
        name="filesystem",
        mcp_server=read_write_filesystem_mcp(root_dir=code_repository),
    )

    async with code_implementation_agent as agent:
        return await agent.run(
            user_prompt=task,
            deps=code_repository,
            toolsets=[toolset],
            output_type=ImplementationResponse,
        )


async def implement_code_change(task: str, code_repository: Path) -> ImplementationResponse:
    """Implement the code following the prompt provided in `task`."""
    return (await implement_code_change_raw(task, code_repository)).output


implement_code_change_tool = FunctionTool.from_function(fn=implement_code_change)


server = FastMCP[Any](name="simple-code-agents", tools=[implement_code_change_tool, investigate_code_repository_tool])


def run():
    server.run()


def run_sse():
    server.run(transport="sse")
