from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from fastmcp.exceptions import ToolError
from fastmcp.tools import Tool
from fastmcp.tools.tool import ToolResult
from mcp.types import (
    ContentBlock,
    ModelPreferences,
    SamplingMessage,
)
from pydantic import BaseModel


class SamplingProtocol(Protocol):
    async def __call__(
        self,
        messages: str | list[str | SamplingMessage],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model_preferences: ModelPreferences | str | list[str] | None = None,
    ) -> ContentBlock: ...


CompletionType = Mapping[str, Any]
CompletionMessageType = Mapping[str, Any] | str


class BaseCompletionExtras(BaseModel):
    raw: dict[str, Any] | None = None
    thinking: str | None = None
    token_usage: int | None = None


class BasePendingToolCall(BaseModel, ABC):  # pyright: ignore[reportUnsafeMultipleInheritance]
    """A base class for a pending tool call to be implemented by a LLMCompletionsProtocol implementation.

    This class is overriden by concrete implementations so they can ensure that the conversation entry created
    with the tool call result is valid for the provider."""

    tool: Tool
    arguments: dict[str, Any]

    @abstractmethod
    def _tool_result_to_completion_message(self, tool_result: ToolResult) -> CompletionMessageType: ...

    @abstractmethod
    def _tool_error_to_completion_message(self, tool_error: ToolError) -> CompletionMessageType: ...

    async def run(self) -> tuple[CompletionMessageType, ToolResult | ToolError]:
        """Runs the tool call and returns the completion message and tool result."""
        try:
            tool_result: ToolResult = await self.tool.run(arguments=self.arguments)

            return self._tool_result_to_completion_message(tool_result), tool_result
        except ToolError as e:
            return self._tool_error_to_completion_message(tool_error=e), e


@runtime_checkable
class LLMCompletionsProtocol(Protocol):
    """A protocol for LLM completions."""

    async def text(
        self,
        system_prompt: str,
        messages: Sequence[CompletionMessageType | str] | CompletionMessageType | str,
        **kwargs: Any,
    ) -> tuple[BaseCompletionExtras, CompletionMessageType, ContentBlock]:
        """Performs a text completion using the configured LLM.

        Args:
            system_prompt: The system prompt to use for the completion.
            messages: The messages to use for the completion.
            **kwargs: Additional keyword arguments to pass to the completion.

        Returns:
            A tuple containing the completion message and the content block.
        """
        ...

    async def tool(
        self,
        system_prompt: str,
        messages: Sequence[CompletionMessageType | str] | CompletionMessageType | str,
        tools: Sequence[Tool] | dict[str, Tool],
        **kwargs: Any,
    ) -> tuple[BaseCompletionExtras, CompletionMessageType, BasePendingToolCall]:
        """Ask the LLM which single tool to call to advance the conversation.

        Args:
            system_prompt: The system prompt to use for the tool call.
            messages: The messages to use for the tool call.
            tools: The tools to use for the tool call.
            **kwargs: Additional keyword arguments to pass to the tool call.

        Returns:
            A tuple containing the completion, the completion conversation entry, and the pending tool call.
        """
        ...

    async def tools(
        self,
        system_prompt: str,
        messages: Sequence[CompletionMessageType | str] | CompletionMessageType | str,
        tools: Sequence[Tool] | dict[str, Tool],
        **kwargs: Any,
    ) -> tuple[BaseCompletionExtras, CompletionMessageType, Sequence[BasePendingToolCall]]:
        """Ask the LLM which tools to call to advance the conversation.

        Args:
            system_prompt: The system prompt to use for the tool call.
            messages: The messages to use for the tool call.
            tools: The tools to use for the tool call.

        Returns:
            A tuple containing the completion, the completion conversation entry, and the list of pending tool calls.
        """
        ...
