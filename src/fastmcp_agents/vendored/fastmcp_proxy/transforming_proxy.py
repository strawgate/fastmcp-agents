from typing import Any, override

from fastmcp.client import Client
from fastmcp.server.proxy import FastMCPProxy, ProxyToolManager
from fastmcp.tools import Tool
from pydantic import Field

from fastmcp_agents.cli.models.tools import ToolTransform


class TransformingFastMCPProxy(FastMCPProxy):
    """
    A FastMCP server that acts as a proxy to a remote MCP-compliant server.
    It uses specialized managers that fulfill requests via an HTTP client.

    It also applies tool transforms to the tools returned by the backend server.
    """

    def __init__(self, client: Client[Any], tool_transforms: dict[str, ToolTransform], **kwargs: Any):  # pyright: ignore[reportAny]
        """
        Initializes the proxy server.

        Args:
            client: The FastMCP client connected to the backend server.
            tool_transforms: A dictionary of tool transforms to apply to the tools.
            **kwargs: Additional settings for the FastMCP server.
        """

        super().__init__(client=client, **kwargs)  # pyright: ignore[reportAny, reportUnknownMemberType]

        self._tool_manager: TransformingProxyToolManager = TransformingProxyToolManager(client=client, tool_transforms=tool_transforms)


class TransformingProxyToolManager(ProxyToolManager):
    """A ToolManager that sources its tools from a remote client in addition to local and mounted tools."""

    tool_transforms: dict[str, ToolTransform] = Field(default_factory=dict)

    def __init__(self, client: Client[Any], tool_transforms: dict[str, ToolTransform], **kwargs: Any):  # pyright: ignore[reportAny]
        super().__init__(client=client, **kwargs)  # pyright: ignore[reportAny, reportUnknownMemberType]
        self.tool_transforms = tool_transforms

    @override
    async def get_tools(self) -> dict[str, Tool]:
        """Gets the unfiltered tool inventory including local, mounted, and proxy tools."""
        transformed_tools: dict[str, Tool] = {}

        tools = await super().get_tools()

        for tool_name, tool in tools.items():
            if transform := self.tool_transforms.get(tool_name):
                if transformed_tool := transform.apply_to_tool(tool):
                    transformed_tools[tool_name] = transformed_tool

            else:
                transformed_tools[tool_name] = tool

        return transformed_tools
