#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform simple code tasks.
"""

import os
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.tools import RunContext

from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPServerToolset
from fastmcp_agents.library.agents.filesystem.prompts import (
    COMPLETION_VERIFICATION,
    GATHER_INFORMATION,
    READ_ONLY_FILESYSTEM_TOOLS,
    RESPONSE_FORMAT,
)
from fastmcp_agents.library.mcp.strawgate.filesystem_operations import read_only_filesystem_mcp, read_write_filesystem_mcp

read_only_filesystem_agent = Agent[Path](
    model=os.getenv("MODEL_CODE_IMPLEMENTATION_AGENT") or os.getenv("MODEL"),
    system_prompt=[
        "You are a filesystem agent. You are able to read the filesystem.",
        """Your goal is to study the assigned task, gather the necessary information to properly understand the task, and then
produce a viable plan to complete the task. You are to be thorough and do this right, you are not to concerned with how much
time it takes to complete the task.""",
    ],
    instructions=[
        GATHER_INFORMATION,
        READ_ONLY_FILESYSTEM_TOOLS,
        COMPLETION_VERIFICATION,
        RESPONSE_FORMAT,
    ],
    deps_type=Path,
    output_type=str,
)


@read_only_filesystem_agent.toolset(per_run_step=False)
async def read_only_filesystem_toolset_func(ctx: RunContext[Path]) -> FastMCPServerToolset[Path]:
    return FastMCPServerToolset[Path].from_mcp_server(name="filesystem", mcp_server=read_only_filesystem_mcp(root_dir=ctx.deps))


read_write_filesystem_agent = Agent[Path](
    model=os.getenv("MODEL_CODE_IMPLEMENTATION_AGENT") or os.getenv("MODEL"),
    system_prompt=[
        "You are a filesystem agent. You are able to read and write to the filesystem.",
        """Your goal is to study the assigned task, gather the necessary information to properly understand the task, and then
produce a viable plan to complete the task. You are to be thorough and do this right, you are not to concerned with how much
time it takes to complete the task.""",
    ],
    instructions=[
        GATHER_INFORMATION,
        READ_ONLY_FILESYSTEM_TOOLS,
        COMPLETION_VERIFICATION,
        RESPONSE_FORMAT,
    ],
    deps_type=Path,
    output_type=str,
)


@read_write_filesystem_agent.toolset
async def read_write_filesystem_toolset_func(ctx: RunContext[Path]) -> FastMCPServerToolset[Path]:
    return FastMCPServerToolset[Path].from_mcp_server(name="filesystem", mcp_server=read_write_filesystem_mcp(root_dir=ctx.deps))
