from __future__ import annotations

import base64
import contextlib
from abc import ABC
from asyncio import Lock, Semaphore
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any, Self, override

import pydantic_core
from fastmcp.client import Client
from fastmcp.client.transports import MCPConfigTransport
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
    from fastmcp import FastMCP
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

    @property
    def id(self) -> str | None:
        return None


class FastMCPClientToolset(BaseFastMCPToolset[AgentDepsT]):
    """A toolset that uses a FastMCP client as the underlying toolset."""

    _fastmcp_client: Client[Any] | None = None

    _enter_lock: Lock
    _running_count: int
    _exit_stack: AsyncExitStack | None
    _semaphore: Semaphore

    def __init__(self, client: Client[Any], tool_retries: int = 2):
        super().__init__(tool_retries=tool_retries)

        self._fastmcp_client = client
        self._enter_lock = Lock()
        self._running_count = 0
        self._semaphore = Semaphore(value=1)

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
        async with self._semaphore:
            try:
                call_tool_result: CallToolResult = await self.fastmcp_client.call_tool(name=name, arguments=tool_args)
            except ToolError as e:
                raise ModelRetry(message=str(object=e)) from e

        # We don't use call_tool_result.data at the moment because it requires the json schema to be translatable
        # back into pydantic models otherwise it will be missing data.

        return call_tool_result.structured_content or _map_fastmcp_tool_results(parts=call_tool_result.content)

    @classmethod
    def from_mcp_server(cls, name: str, mcp_server: MCPServerTypes) -> Self:
        return cls.from_mcp_config(mcp_config=MCPConfig(mcpServers={name: mcp_server}))

    @classmethod
    def from_mcp_config(cls, mcp_config: MCPConfig) -> Self:
        fastmcp_client: Client[MCPConfigTransport] = Client[MCPConfigTransport](transport=mcp_config)
        return cls(client=fastmcp_client, tool_retries=2)


class FastMCPServerToolset(BaseFastMCPToolset[AgentDepsT], ABC):
    """An abstract base class for toolsets that use a FastMCP server to provide the underlying toolset."""

    _fastmcp_server: FastMCP[Any]
    _semaphore: Semaphore

    def __init__(self, server: FastMCP[Any], tool_retries: int = 2):
        super().__init__(tool_retries=tool_retries)
        self._fastmcp_server = server
        self._semaphore = Semaphore(value=1)

    async def __aenter__(self) -> Self:
        await self._fastmcp_server.get_tools()
        return self

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
            msg = f"Tool {name} not found in toolset {self._fastmcp_server.name}"
            raise ValueError(msg)

        async with self._semaphore:
            try:
                call_tool_result: ToolResult = await matching_tool.run(arguments=tool_args)
            except ToolError as e:
                raise ModelRetry(message=str(object=e)) from e

        return call_tool_result.structured_content or _map_fastmcp_tool_results(parts=call_tool_result.content)

    @classmethod
    def from_mcp_server(cls, name: str, mcp_server: MCPServerTypes) -> Self:
        return cls.from_mcp_config(mcp_config=MCPConfig(mcpServers={name: mcp_server}))

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
