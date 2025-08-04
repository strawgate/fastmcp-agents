#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform simple code tasks.
"""

import os
from pathlib import Path

from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPServerToolset
from fastmcp_agents.library.agents.shared.models import Failure
from fastmcp_agents.library.agents.simple_code.models import (
    BranchInfo,
    DirectoryStructure,
    ImplementationResponse,
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
from fastmcp_agents.library.mcp.strawgate.filesystem_operations import read_only_filesystem_mcp, read_write_filesystem_mcp
from pydantic_ai import Agent
from pydantic_ai.tools import RunContext


def add_repo_structure(ctx: RunContext[Path]) -> str:  # pyright: ignore[reportUnusedFunction]
    structure: DirectoryStructure = DirectoryStructure.from_dir(directory=ctx.deps)

    return f"The basic structure of the codebase is: {structure}."


def add_branch_info(ctx: RunContext[Path]) -> str:  # pyright: ignore[reportUnusedFunction]
    branch_info: BranchInfo | None = BranchInfo.from_dir(directory=ctx.deps)

    if branch_info is None:
        return "Could not determine the Git branch information."

    return f"The Branch is: {branch_info.name} and the commit SHA is: {branch_info.commit_sha}."


code_implementation_agent = Agent[Path, ImplementationResponse | Failure](
    model=os.getenv("MODEL_CODE_IMPLEMENTATION_AGENT") or os.getenv("MODEL"),
    system_prompt=[
        WHO_YOU_ARE,
        YOUR_GOAL,
    ],
    instructions=[
        GATHER_INFORMATION,
        READ_ONLY_FILESYSTEM_TOOLS,
        READ_WRITE_FILESYSTEM_TOOLS,
        COMPLETION_VERIFICATION,
        RESPONSE_FORMAT,
        add_branch_info,
        add_repo_structure,
    ],
    deps_type=Path,
    output_type=[ImplementationResponse, Failure],
)


@code_implementation_agent.toolset(per_run_step=False)
async def read_write_filesystem_toolset_func(ctx: RunContext[Path]) -> FastMCPServerToolset[Path]:
    return FastMCPServerToolset[Path].from_mcp_server(name="filesystem", mcp_server=read_write_filesystem_mcp(root_dir=ctx.deps))


code_investigation_agent = Agent[Path, InvestigationResult | Failure](
    model=os.getenv("MODEL_CODE_IMPLEMENTATION_AGENT") or os.getenv("MODEL"),
    system_prompt=[
        WHO_YOU_ARE,
        YOUR_GOAL,
    ],
    instructions=[
        GATHER_INFORMATION,
        READ_ONLY_FILESYSTEM_TOOLS,
        COMPLETION_VERIFICATION,
        RESPONSE_FORMAT,
        add_branch_info,
        add_repo_structure,
    ],
    deps_type=Path,
    output_type=[InvestigationResult, Failure],
)


@code_investigation_agent.toolset
async def read_only_filesystem_toolset_func(ctx: RunContext[Path]) -> FastMCPServerToolset[Path]:
    return FastMCPServerToolset[Path].from_mcp_server(name="filesystem", mcp_server=read_only_filesystem_mcp(root_dir=ctx.deps))


# def code_investigation_agent_factory(
#     extra_system_prompt: Sequence[str] | None = None,
#     extra_toolsets: Sequence[AbstractToolset[Path]] | None = None,
# ) -> Agent[Path, InvestigationResult | Failure]:
#     extra_system_prompt = [] if extra_system_prompt is None else extra_system_prompt
#     extra_toolsets = [] if extra_toolsets is None else extra_toolsets


# def code_agent_factory(
#     extra_system_prompt: Sequence[str] | None = None,
#     extra_toolsets: Sequence[AbstractToolset[Path]] | None = None,
# ) -> Agent[Path, ImplementationResponse | Failure]:
#     extra_system_prompt = [] if extra_system_prompt is None else extra_system_prompt
#     extra_toolsets = [] if extra_toolsets is None else extra_toolsets

#     return Agent[Path, ImplementationResponse | Failure](
#         model=os.getenv("MODEL_CODE_IMPLEMENTATION_AGENT") or os.getenv("MODEL"),
#         system_prompt=[
#             WHO_YOU_ARE,
#             YOUR_GOAL,
#             GATHER_INFORMATION,
#             READ_ONLY_FILESYSTEM_TOOLS,
#             READ_WRITE_FILESYSTEM_TOOLS,
#             COMPLETION_VERIFICATION,
#             RESPONSE_FORMAT,
#             *extra_system_prompt,
#         ],
#         instructions=[add_branch_info, add_repo_structure],
#         deps_type=Path,
#             toolsets=[FilesystemToolset(), *extra_toolsets],
#         output_type=[ImplementationResponse, Failure],
#     )
