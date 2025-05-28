from typing import Any, Literal, Protocol

from mcp.types import EmbeddedResource, ImageContent, TextContent

from fastmcp_agents.tool_transformer.base import (
    BaseExtraToolParameter,
    BaseToolParameterOverride,
)


class ExtraParameterNumber(BaseExtraToolParameter):
    """An extra parameter that is a number."""

    type: Literal["number"] = "number"  # type: ignore
    default: int | float | None = None  # type: ignore


class ExtraParameterString(BaseExtraToolParameter):
    """An extra parameter that is a string."""

    type: Literal["string"] = "string"  # type: ignore
    default: str | None = None  # type: ignore


class ExtraParameterBoolean(BaseExtraToolParameter):
    """An extra parameter that is a boolean."""

    type: Literal["boolean"] = "boolean"  # type: ignore
    default: bool | None = None  # type: ignore


ExtraToolParameterTypes = ExtraParameterBoolean | ExtraParameterString | ExtraParameterNumber


class PostToolCallHookProtocol(Protocol):
    async def __call__(
        self,
        response: list[TextContent | ImageContent | EmbeddedResource],
        tool_args: dict[str, Any],
        hook_args: dict[str, Any],
    ) -> None: ...


class PreToolCallHookProtocol(Protocol):
    async def __call__(
        self,
        tool_args: dict[str, Any],
        hook_args: dict[str, Any],
    ) -> None: ...


class ToolParameterOverride(BaseToolParameterOverride):
    """A parameter override for a tool."""
