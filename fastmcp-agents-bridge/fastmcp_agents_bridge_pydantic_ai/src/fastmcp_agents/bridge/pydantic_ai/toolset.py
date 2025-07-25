from __future__ import annotations

import base64
import contextlib
from typing import TYPE_CHECKING, Any, ClassVar, override

import pydantic_core
from fastmcp import FastMCP  # noqa: TC002
from fastmcp.exceptions import ToolError
from fastmcp.mcp_config import MCPConfig
from fastmcp.utilities.mcp_config import composite_server_from_mcp_config  # pyright: ignore[reportUnknownVariableType]
from mcp.types import AudioContent, ContentBlock, EmbeddedResource, ImageContent, TextContent, TextResourceContents
from pydantic import BaseModel, ConfigDict, Field

from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.mcp import TOOL_SCHEMA_VALIDATOR, messages
from pydantic_ai.tools import AgentDepsT, ToolDefinition
from pydantic_ai.toolsets import AbstractToolset
from pydantic_ai.toolsets.abstract import ToolsetTool

if TYPE_CHECKING:
    from fastmcp.mcp_config import MCPServerTypes
    from fastmcp.tools import Tool as FastMCPTool
    from fastmcp.tools.tool import ToolResult
    from fastmcp.tools.tool_transform import ToolTransformConfig

    from pydantic_ai.tools import RunContext


FastMCPToolResult = messages.BinaryContent | dict[str, Any] | str | None

FastMCPToolResults = list[FastMCPToolResult] | FastMCPToolResult


class FastMCPToolset(BaseModel, AbstractToolset[AgentDepsT]):  # pyright: ignore[reportUnsafeMultipleInheritance]
    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)
    fastmcp: FastMCP[Any] = Field(..., description="The fastmcp instance to bridge to")
    tool_retries: int = Field(default=2, description="The number of times to retry a failed tool call")

    @override
    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        fastmcp_tools: dict[str, FastMCPTool] = await self.fastmcp.get_tools()

        return {
            tool.name: convert_fastmcp_tool_to_toolset_tool(toolset=self, fastmcp_tool=tool, retries=self.tool_retries)
            for tool in fastmcp_tools.values()
        }

    async def get_tool(self, key: str, transformation: ToolTransformConfig | None = None) -> ToolsetTool[AgentDepsT]:
        fastmcp_tool: FastMCPTool = await self.fastmcp.get_tool(key=key)

        if transformation:
            fastmcp_tool = transformation.apply(fastmcp_tool)

        return convert_fastmcp_tool_to_toolset_tool(toolset=self, fastmcp_tool=fastmcp_tool, retries=self.tool_retries)

    def add_tool_transformation(self, tool_name: str, transformation: ToolTransformConfig) -> None:
        self.fastmcp.add_tool_transformation(tool_name=tool_name, transformation=transformation)

    def remove_tool_transformation(self, tool_name: str) -> None:
        self.fastmcp.remove_tool_transformation(tool_name=tool_name)

    @override
    async def call_tool(self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]) -> Any:  # pyright: ignore[reportAny]
        fastmcp_tool: FastMCPTool = await self.fastmcp.get_tool(key=name)
        try:
            call_tool_result: ToolResult = await fastmcp_tool.run(arguments=tool_args)
        except ToolError as e:
            raise ModelRetry(message=str(object=e)) from e
        return call_tool_result.structured_content or _map_fastmcp_tool_results(parts=call_tool_result.content)

    async def call_tool_direct(self, name: str, tool_args: dict[str, Any]) -> Any:  # pyright: ignore[reportAny]
        fastmcp_tool: FastMCPTool = await self.fastmcp.get_tool(key=name)
        try:
            call_tool_result: ToolResult = await fastmcp_tool.run(arguments=tool_args)
        except ToolError as e:
            raise ModelRetry(message=str(object=e)) from e
        return call_tool_result.structured_content or _map_fastmcp_tool_results(parts=call_tool_result.content)

    @classmethod
    def from_mcp_config(cls, mcp_config: MCPConfig | dict[str, MCPServerTypes] | dict[str, Any]) -> FastMCPToolset[AgentDepsT]:
        if not isinstance(mcp_config, MCPConfig):
            mcp_config = MCPConfig(mcpServers=mcp_config)

        mcp_server_host: FastMCP[Any] = composite_server_from_mcp_config(config=mcp_config, name_as_prefix=False)

        return cls(fastmcp=mcp_server_host)

    @classmethod
    def from_mcp_server(cls, name: str, mcp_server: MCPServerTypes) -> FastMCPToolset[AgentDepsT]:
        mcp_config = MCPConfig(mcpServers={name: mcp_server})
        return cls.from_mcp_config(mcp_config=mcp_config)


def convert_fastmcp_tool_to_toolset_tool(
    toolset: FastMCPToolset[AgentDepsT], fastmcp_tool: FastMCPTool, retries: int
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
