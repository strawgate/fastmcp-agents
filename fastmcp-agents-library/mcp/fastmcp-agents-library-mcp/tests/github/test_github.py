from fastmcp.client import Client
from fastmcp.mcp_config import MCPConfig, TransformingStdioMCPServer
from inline_snapshot import snapshot
from mcp.types import Tool

from fastmcp_agents.library.mcp.github.mcp import github_mcp, restrict_github_mcp


def to_mcp_config(mcp_server: TransformingStdioMCPServer) -> MCPConfig:
    return MCPConfig(mcpServers={"github": mcp_server})


async def list_tools(mcp_config: MCPConfig) -> list[Tool]:
    async with Client(transport=mcp_config) as client:
        return await client.list_tools()


async def list_mcp_tools(mcp_server: TransformingStdioMCPServer) -> list[Tool]:
    mcp_config: MCPConfig = to_mcp_config(mcp_server)

    tools = await list_tools(mcp_config)

    assert len(tools) > 0

    return tools


async def test_github():
    tools = await list_mcp_tools(github_mcp())
    assert len(tools) > 50


def assert_in_tools(tools: list[Tool], tool_name: str):
    assert tool_name in [tool.name for tool in tools]


def assert_not_in_tools(tools: list[Tool], tool_name: str):
    assert tool_name not in [tool.name for tool in tools]


def get_tool_by_name(tools: list[Tool], tool_name: str) -> Tool | None:
    for tool in tools:
        if tool.name == tool_name:
            return tool
    return None


class TestGitHubRestricted:
    async def test_init(self):
        tools = await list_mcp_tools(restrict_github_mcp())
        assert len(tools) > 50

    async def test_read(self):
        tools = await list_mcp_tools(restrict_github_mcp(read=True))

        assert_in_tools(tools, "get_issue")
        assert_not_in_tools(tools, "update_issue")

    async def test_write(self):
        tools = await list_mcp_tools(restrict_github_mcp(write=True))

        assert_not_in_tools(tools, "get_issue")
        assert_in_tools(tools, "update_issue")

    async def test_owner_restricted(self):
        tools = await list_mcp_tools(restrict_github_mcp(owner="fastmcp", read=True))

        assert_in_tools(tools, "get_issue")
        assert_not_in_tools(tools, "search_code")

    async def test_owner_repo_restricted(self):
        tools = await list_mcp_tools(restrict_github_mcp(owner="jlowin", repository="fastmcp", read=True))

        issue_tool = get_tool_by_name(tools, "get_issue")

        assert issue_tool is not None

        assert issue_tool.model_dump() == snapshot(
            {
                "name": "get_issue",
                "title": "Get issue details",
                "description": "Get details of a specific issue in a GitHub repository.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"issue_number": {"description": "The number of the issue", "type": "number"}},
                    "required": ["issue_number"],
                },
                "outputSchema": None,
                "annotations": {
                    "title": "Get issue details",
                    "readOnlyHint": True,
                    "destructiveHint": None,
                    "idempotentHint": None,
                    "openWorldHint": None,
                },
                "meta": {"_fastmcp": {"tags": ["object: issue", "scope: read", "verb: get"]}},
            }
        )

        assert_not_in_tools(tools, "search_code")

    async def test_owner_repo_issue_restricted(self):
        tools = await list_mcp_tools(
            restrict_github_mcp(
                owner="jlowin",
                repository="fastmcp",
                issue_number=1,
                read=True,
            )
        )

        assert_in_tools(tools, "get_issue")

        issue_tool = get_tool_by_name(tools, "get_issue")

        assert issue_tool is not None

        assert issue_tool.model_dump() == snapshot(
            {
                "name": "get_issue",
                "title": "Get issue details",
                "description": "Get details of a specific issue in a GitHub repository.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
                "outputSchema": None,
                "annotations": {
                    "title": "Get issue details",
                    "readOnlyHint": True,
                    "destructiveHint": None,
                    "idempotentHint": None,
                    "openWorldHint": None,
                },
                "meta": {"_fastmcp": {"tags": ["object: issue", "scope: read", "verb: get"]}},
            }
        )

        assert_not_in_tools(tools, "create_issue")
