import os
from pathlib import Path

from fastmcp.mcp_config import TransformingStdioMCPServer
from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig


def git_mcp(
    tools: dict[str, ToolTransformConfig] | None = None,
    cwd: Path | None = None,
    include_tags: set[str] | None = None,
    exclude_tags: set[str] | None = None,
) -> TransformingStdioMCPServer:
    return TransformingStdioMCPServer(
        command="uvx",
        args=["mcp-server-git"],
        cwd=str(cwd) if cwd else None,
        env=dict(os.environ.copy()),
        tools=tools or {},
        include_tags=include_tags,
        exclude_tags=exclude_tags,
    )


READ_REPOSITORY_TOOLS = {
    "git_status",
    "git_diff_unstaged",
    "git_diff_staged",
    "git_diff",
    "git_show",
}

WRITE_REPOSITORY_TOOLS = {"git_init", "git_checkout"}

READ_COMMIT_TOOLS = {
    "git_log",
    "git_show",
}

WRITE_COMMIT_TOOLS = {
    "git_add",
    "git_reset",
    "git_commit",
}

READ_BRANCHING_TOOLS = {
    "git_branch",
}

WRITE_BRANCHING_TOOLS = {
    "git_create_branch",
}


def git_tools(
    repository: bool = False,
    commit: bool = False,
    branching: bool = False,
    read_tools: bool = True,
    write_tools: bool = True,
) -> set[str]:
    tools: set[str] = set()

    if repository:
        if read_tools:
            tools.update(READ_REPOSITORY_TOOLS)
        if write_tools:
            tools.update(WRITE_REPOSITORY_TOOLS)
    if commit:
        if read_tools:
            tools.update(READ_COMMIT_TOOLS)
        if write_tools:
            tools.update(WRITE_COMMIT_TOOLS)
    if branching and write_tools:
        tools.update(WRITE_BRANCHING_TOOLS)

    return tools


def restrict_git_mcp_server(
    git_mcp_server: TransformingStdioMCPServer | None = None,
    cwd: Path | None = None,
    repository: bool = False,
    commit: bool = False,
    branching: bool = False,
    read_tools: bool = True,
    write_tools: bool = True,
) -> TransformingStdioMCPServer:
    if not git_mcp_server:
        git_mcp_server = git_mcp(cwd=cwd)

    tools = git_tools(
        repository=repository,
        commit=commit,
        branching=branching,
        read_tools=read_tools,
        write_tools=write_tools,
    )

    tool_transformations: dict[str, ToolTransformConfig] = dict.fromkeys(
        tools,
        ToolTransformConfig(
            tags={"restricted"},
        ),
    )

    git_mcp_server.tools = tool_transformations

    return git_mcp_server


def repo_path_restricted_git_mcp_server(
    repo_path: Path,
    git_mcp_server: TransformingStdioMCPServer | None = None,
    repository: bool = False,
    commit: bool = False,
    branching: bool = False,
    read_tools: bool = False,
    write_tools: bool = False,
) -> TransformingStdioMCPServer:
    if not git_mcp_server:
        git_mcp_server = git_mcp()

    git_mcp_server.tools = dict.fromkeys(
        git_tools(
            repository=repository,
            commit=commit,
            branching=branching,
            read_tools=read_tools,
            write_tools=write_tools,
        ),
        ToolTransformConfig(
            arguments={
                "repo_path": ArgTransformConfig(default=str(repo_path), hide=True),
            },
            tags={"restricted"},
        ),
    )

    git_mcp_server.include_tags = {"restricted"}

    return git_mcp_server
