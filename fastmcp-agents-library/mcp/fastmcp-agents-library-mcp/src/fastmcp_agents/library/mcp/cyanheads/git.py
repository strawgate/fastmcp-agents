import os

from fastmcp.mcp_config import TransformingStdioMCPServer
from fastmcp.tools.tool_transform import ToolTransformConfig


def git_mcp(
    tools: dict[str, ToolTransformConfig] | None = None,
    include_tags: set[str] | None = None,
    exclude_tags: set[str] | None = None,
) -> TransformingStdioMCPServer:
    return TransformingStdioMCPServer(
        command="npx",
        args=["@cyanheads/git-mcp-server"],
        env=dict(os.environ.copy()),
        tools=tools or {},
        include_tags=include_tags,
        exclude_tags=exclude_tags,
    )


READ_REPOSITORY_TOOLS = {
    "git_status",
}

WRITE_REPOSITORY_TOOLS = {
    "git_init",
    "git_clone",
    "git_add",
    "git_clean",
}

READ_COMMIT_TOOLS = {
    "git_log",
    "git_diff",
    "git_show",
}

WRITE_COMMIT_TOOLS = {
    "git_commit",
}


WRITE_BRANCHING_TOOLS = {
    "git_branch",
    "git_checkout",
    "git_merge",
    "git_rebase",
    "git_cherry_pick",
}

WRITE_REMOTE_TOOLS = {
    "git_remote",
    "git_fetch",
    "git_pull",
    "git_push",
}


def git_tools(
    repository: bool = False,
    commit: bool = False,
    branching: bool = False,
    remote: bool = False,
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
    if remote and write_tools:
        tools.update(WRITE_REMOTE_TOOLS)

    return tools


def restrict_git_mcp_server(
    git_mcp_server: TransformingStdioMCPServer | None = None,
    repository: bool = False,
    commit: bool = False,
    branching: bool = False,
    remote: bool = False,
    read_tools: bool = True,
    write_tools: bool = True,
) -> TransformingStdioMCPServer:
    if not git_mcp_server:
        git_mcp_server = git_mcp()

    tools = git_tools(
        repository=repository,
        commit=commit,
        branching=branching,
        remote=remote,
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
