from __future__ import annotations

import base64
import contextlib
from abc import ABC
from contextlib import AsyncExitStack
from dataclasses import field
from typing import TYPE_CHECKING, Any, Self, override

import pydantic_core
from fastmcp.exceptions import ToolError
from fastmcp.mcp_config import MCPConfig
from fastmcp.server.server import FastMCP
from fastmcp.utilities.mcp_config import composite_server_from_mcp_config  # pyright: ignore[reportUnknownVariableType]
from mcp.types import AudioContent, ContentBlock, EmbeddedResource, ImageContent, TextContent, TextResourceContents
from mcp.types import Tool as MCPTool

from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.mcp import TOOL_SCHEMA_VALIDATOR, messages
from pydantic_ai.tools import AgentDepsT, RunContext, ToolDefinition
from pydantic_ai.toolsets import AbstractToolset
from pydantic_ai.toolsets.abstract import ToolsetTool

if TYPE_CHECKING:
    from asyncio import Lock

    from fastmcp import FastMCP
    from fastmcp.client import Client
    from fastmcp.client.client import CallToolResult
    from fastmcp.client.transports import FastMCPTransport
    from fastmcp.mcp_config import MCPServerTypes
    from fastmcp.tools import Tool as FastMCPTool
    from fastmcp.tools.tool import ToolResult


FastMCPToolResult = messages.BinaryContent | dict[str, Any] | str | None

FastMCPToolResults = list[FastMCPToolResult] | FastMCPToolResult


class BaseFastMCPToolset[AgentDepsT](AbstractToolset[AgentDepsT], ABC):
    """An abstract base class for toolsets that use FastMCP for tool discovery and execution."""

    _tool_retries: int = 2

    def __init__(self, tool_retries: int = 2):
        self._tool_retries = tool_retries


class FastMCPClientToolset(BaseFastMCPToolset[AgentDepsT]):
    """A toolset that uses a FastMCP client as the underlying toolset."""

    _fastmcp_client: Client[FastMCPTransport] | None = None

    _enter_lock: Lock = field(compare=False)
    _running_count: int
    _exit_stack: AsyncExitStack | None

    def __init__(self, client: Client[FastMCPTransport], tool_retries: int = 2):
        super().__init__(tool_retries=tool_retries)

        self._fastmcp_client = client

    async def __aenter__(self) -> Self:
        async with self._enter_lock:
            if self._running_count == 0 and self._fastmcp_client:
                self._exit_stack = AsyncExitStack()
                await self._exit_stack.enter_async_context(self._fastmcp_client)
                self._running_count += 1

        return self

    async def __aexit__(self, *args: Any) -> bool | None:
        async with self._enter_lock:
            self._running_count -= 1
            if self._running_count == 0 and self._exit_stack:
                await self._exit_stack.aclose()
                self._exit_stack = None

        return None

    @property
    def fastmcp_client(self) -> Client[FastMCPTransport]:
        if not self._fastmcp_client:
            msg = "FastMCP client not initialized"
            raise RuntimeError(msg)

        return self._fastmcp_client

    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        mcp_tools: list[MCPTool] = await self.fastmcp_client.list_tools()

        return {tool.name: convert_mcp_tool_to_toolset_tool(toolset=self, mcp_tool=tool, retries=self._tool_retries) for tool in mcp_tools}

    async def call_tool(self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]) -> Any:  # pyright: ignore[reportAny]
        call_tool_result: CallToolResult = await self.fastmcp_client.call_tool(name=name, arguments=tool_args)

        return call_tool_result.data or call_tool_result.structured_content or _map_fastmcp_tool_results(parts=call_tool_result.content)


class FastMCPServerToolset(BaseFastMCPToolset[AgentDepsT], ABC):
    """An abstract base class for toolsets that use a FastMCP server to provide the underlying toolset."""

    _fastmcp_server: FastMCP[Any]

    def __init__(self, server: FastMCP[Any], tool_retries: int = 2):
        super().__init__(tool_retries=tool_retries)
        self._fastmcp_server = server

    async def _setup_fastmcp_server(self, ctx: RunContext[AgentDepsT]) -> None:
        msg = "Subclasses must implement this method"
        raise NotImplementedError(msg)

    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        fastmcp_tools: dict[str, FastMCPTool] = await self._fastmcp_server.get_tools()  # pyright: ignore[reportUnknownVariableType]

        return {
            tool_name: convert_fastmcp_tool_to_toolset_tool(
                toolset=self,
                fastmcp_tool=tool,
                retries=self._tool_retries,
            )
            for tool_name, tool in fastmcp_tools.items()
        }

    @override
    async def call_tool(self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]) -> Any:  # pyright: ignore[reportAny]
        fastmcp_tools: dict[str, FastMCPTool] = await self._fastmcp_server.get_tools()

        if not (matching_tool := fastmcp_tools.get(name)):
            msg = f"Tool {name} not found in toolset {self.name}"
            raise ValueError(msg)

        try:
            call_tool_result: ToolResult = await matching_tool.run(arguments=tool_args)
        except ToolError as e:
            raise ModelRetry(message=str(object=e)) from e

        return call_tool_result.structured_content or _map_fastmcp_tool_results(parts=call_tool_result.content)

    @classmethod
    def from_mcp_server(cls, name: str, mcp_server: MCPServerTypes) -> Self:
        mcp_config: MCPConfig = MCPConfig(mcpServers={name: mcp_server})
        return cls.from_mcp_config(mcp_config=mcp_config)

    @classmethod
    def from_mcp_config(cls, mcp_config: MCPConfig) -> Self:
        fastmcp_server: FastMCP[None] = composite_server_from_mcp_config(config=mcp_config, name_as_prefix=False)
        return cls(server=fastmcp_server)


def convert_mcp_tool_to_toolset_tool(
    toolset: BaseFastMCPToolset[AgentDepsT],
    mcp_tool: MCPTool,
    retries: int,
) -> ToolsetTool[AgentDepsT]:
    return ToolsetTool[AgentDepsT](
        tool_def=ToolDefinition(
            name=mcp_tool.name,
            description=mcp_tool.description,
            parameters_json_schema=mcp_tool.inputSchema,
        ),
        toolset=toolset,
        max_retries=retries,
        args_validator=TOOL_SCHEMA_VALIDATOR,
    )


def convert_fastmcp_tool_to_toolset_tool(
    toolset: BaseFastMCPToolset[AgentDepsT],
    fastmcp_tool: FastMCPTool,
    retries: int,
) -> ToolsetTool[AgentDepsT]:
    return ToolsetTool[AgentDepsT](
        tool_def=ToolDefinition(
            name=fastmcp_tool.name,
            description=fastmcp_tool.description,
            parameters_json_schema=fastmcp_tool.parameters,
        ),
        toolset=toolset,
        max_retries=retries,
        args_validator=TOOL_SCHEMA_VALIDATOR,
    )


def _map_fastmcp_tool_results(parts: list[ContentBlock]) -> list[FastMCPToolResult]:
    return [_map_fastmcp_tool_result(part) for part in parts]


def _map_fastmcp_tool_result(part: ContentBlock) -> FastMCPToolResult:
    if isinstance(part, TextContent):
        text = part.text
        if text.startswith(("[", "{")):
            with contextlib.suppress(ValueError):
                result: Any = pydantic_core.from_json(text)  # pyright: ignore[reportAny]
                if isinstance(result, dict | list):
                    return result  # pyright: ignore[reportUnknownVariableType, reportReturnType]
        return text

    if isinstance(part, ImageContent):
        return messages.BinaryContent(data=base64.b64decode(part.data), media_type=part.mimeType)

    if isinstance(part, AudioContent):
        return messages.BinaryContent(data=base64.b64decode(part.data), media_type=part.mimeType)

    if isinstance(part, EmbeddedResource):
        resource = part.resource
        if isinstance(resource, TextResourceContents):
            return resource.text

        # BlobResourceContents
        return messages.BinaryContent(
            data=base64.b64decode(resource.blob),
            media_type=resource.mimeType or "application/octet-stream",
        )

    msg = f"Unsupported/Unknown content block type: {type(part)}"
    raise ValueError(msg)
