import os

from fastmcp.mcp_config import TransformingStdioMCPServer
from fastmcp.tools.tool_transform import ToolTransformConfig

from fastmcp_agents.library.mcp.github.tools.base import filter_tools
from fastmcp_agents.library.mcp.github.tools.issues import ISSUE_TOOLS
from fastmcp_agents.library.mcp.github.tools.pull_requests import PULL_REQUEST_TOOLS
from fastmcp_agents.library.mcp.github.tools.repositories import REPOSITORY_TOOLS

ALL_TOOLS: dict[str, ToolTransformConfig] = ISSUE_TOOLS | PULL_REQUEST_TOOLS | REPOSITORY_TOOLS


def github_tools_with_arguments(
    owner: str | None = None,
    repository: str | None = None,
    issue_number: int | None = None,
) -> dict[str, ToolTransformConfig]:
    """Restrict the tools to the given owner, repository, and issue number.

    If owner, repository, or issue_number are provided, only tools that have those arguments will be returned.
    """
    tools: dict[str, ToolTransformConfig] = ALL_TOOLS

    if not any([owner, repository, issue_number]):
        return tools

    require_arguments: set[str] = set()
    if owner:
        require_arguments.add("owner")
    if repository:
        require_arguments.add("repo")
    if issue_number:
        require_arguments.add("issue_number")

    filtered_tools = filter_tools(
        tools=tools,
        required_arguments=require_arguments,
    )

    for tool in filtered_tools.values():
        if owner:
            tool.arguments["owner"].default = owner
            tool.arguments["owner"].hide = True
        if repository:
            tool.arguments["repo"].default = repository
            tool.arguments["repo"].hide = True
        if issue_number:
            tool.arguments["issue_number"].default = issue_number
            tool.arguments["issue_number"].hide = True

    return filtered_tools


def github_mcp(
    tools: dict[str, ToolTransformConfig] | None = None,
    include_tags: set[str] | None = None,
    exclude_tags: set[str] | None = None,
) -> TransformingStdioMCPServer:
    return TransformingStdioMCPServer(
        command="docker",
        args=[
            "run",
            "-i",
            "--rm",
            "-e",
            "GITHUB_PERSONAL_ACCESS_TOKEN",
            "ghcr.io/github/github-mcp-server",
        ],
        env=dict(os.environ.copy()),
        tools=tools or {},
        include_tags=include_tags,
        exclude_tags=exclude_tags,
    )


def restrict_github_mcp(
    github_mcp_server: TransformingStdioMCPServer | None = None,
    owner: str | None = None,
    repository: str | None = None,
    issue_number: int | None = None,
    read: bool = False,
    write: bool = False,
    search: bool = False,
) -> TransformingStdioMCPServer:
    """Restrict the GitHub MCP server to the given owner, repository, issue number, and read/write/search permissions.

    If owner, repository, or issue_number are provided, only tools that have those arguments will be returned.
    If read, write, or search are provided, only tools that match will be included.
    """
    if github_mcp_server is None:
        github_mcp_server = github_mcp()

    tools = github_tools_with_arguments(
        owner=owner,
        repository=repository,
        issue_number=issue_number,
    )

    github_mcp_server.tools = tools

    if any([read, write, search]):
        github_mcp_server.include_tags = github_mcp_server.include_tags or set()

        if read:
            github_mcp_server.include_tags.add("scope: read")
        if write:
            github_mcp_server.include_tags.add("scope: write")
        if search:
            github_mcp_server.include_tags.add("scope: search")

    return github_mcp_server
