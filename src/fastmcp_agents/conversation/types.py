"""Models for Conversation entries and tool calls."""

import json
from collections.abc import Sequence
from typing import Any, Literal, TypeAlias

from mcp.types import EmbeddedResource, ImageContent, TextContent
from openai.types.chat.chat_completion_message_tool_call_param import ChatCompletionMessageToolCallParam
from pydantic import BaseModel, ConfigDict, Field, model_serializer

MCPToolResponseTypes = TextContent | ImageContent | EmbeddedResource


class BaseConvoModel(BaseModel):
    """A base class for Conversation models."""

    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)


class ToolRequestPart(BaseConvoModel):
    """A helper class for a tool call request."""

    id: str = Field(...)
    """The id of the tool call request. This is used to match the tool call request to the tool call response."""

    name: str = Field(...)
    """The name of the tool to call."""

    arguments: dict[str, Any] = Field(...)
    """The arguments to pass to the tool."""

    @classmethod
    def from_openai(cls, message: ChatCompletionMessageToolCallParam) -> "ToolRequestPart":
        function = message["function"]
        return cls(id=message["id"], name=function["name"], arguments=json.loads(function["arguments"]))

    @model_serializer
    def serialize(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments),
            },
            "type": "function",
        }


# class ToolResponsePart(BaseConvoModel):
#     """A helper class for a tool call response."""

#     tool_request_id: str = Field(..., alias="tool_call_id")
#     """The id of the tool call request. This is used to match the tool call request to the tool call response."""

#     name: str = Field(...)
#     """The name of the tool to call."""

#     arguments: dict[str, Any] = Field(..., exclude=True)
#     """The arguments that were passed to the tool."""

#     content: list[MCPToolResponseTypes] = Field(...)
#     """The content of the tool call response."""


class SystemConversationEntry(BaseConvoModel):
    """A chat entry is a message in the chat history."""

    role: Literal["system"] = Field(default="system")
    """A conversation entry that is a system message"""

    content: str = Field(...)
    """The content of the chat entry"""


class UserConversationEntry(BaseConvoModel):
    """A chat entry is a message in the chat history."""

    role: Literal["user"] = Field(default="user")
    """A conversation entry that is a user message"""

    content: str = Field(...)
    """The content of the chat entry"""


class ToolConversationEntry(BaseConvoModel):
    """A tool call chat entry is a message in the chat history that is a tool call."""

    role: Literal["tool"] = Field(default="tool")
    """A conversation entry that is a tool call"""

    tool_call_id: str = Field(...)
    """The id of the tool call request."""

    name: str = Field(...)
    """The name of the tool to call."""

    arguments: dict[str, Any] = Field(..., exclude=True)
    """The arguments that were passed to the tool."""

    content: list[MCPToolResponseTypes] = Field(...)
    """The content of the tool call response."""

    success: bool = Field(..., exclude=True)
    """Whether the tool call was successful."""

    @classmethod
    def from_tool_request_part(
        cls, tool_request_part: ToolRequestPart, result: list[MCPToolResponseTypes], success: bool
    ) -> "ToolConversationEntry":
        """Create a tool conversation entry from a tool request part."""
        return cls(
            tool_call_id=tool_request_part.id,
            name=tool_request_part.name,
            arguments=tool_request_part.arguments,
            content=result,
            success=success,
        )


class AssistantConversationEntry(BaseConvoModel):
    """A chat entry is a message in the chat history."""

    role: Literal["assistant"] = Field(default="assistant")
    """A conversation entry that is an assistant message"""

    content: str | None = Field(default=None)
    """The content of the chat entry"""

    tool_calls: list[ToolRequestPart] = Field(default_factory=list)
    """The tool calls that were made in the assistant message"""

    token_usage: int | None = Field(default=None, exclude=True)
    """The number of tokens used by the assistant message"""

    @classmethod
    def count_tokens(cls, entries: list["AssistantConversationEntry"]) -> int:
        """Count the number of tokens in the conversation."""

        return sum(entry.token_usage for entry in entries if entry.token_usage is not None)


ConversationEntryTypes: TypeAlias = SystemConversationEntry | UserConversationEntry | AssistantConversationEntry | ToolConversationEntry


class Conversation(BaseConvoModel):
    """Conversations are an immutable list of conversation entries."""

    entries: list[ConversationEntryTypes] = Field(default_factory=list)
    """The conversation entries"""

    def append(self, message: ConversationEntryTypes) -> "Conversation":
        """Returns a new conversation with the message appended."""
        return self.model_copy(update={"entries": [*self.entries, message]})

    def extend(self, entries: Sequence[ConversationEntryTypes]) -> "Conversation":
        """Returns a new conversation with the messages extended."""
        return self.model_copy(update={"entries": [*self.entries, *entries]})

    def get(self) -> Sequence[ConversationEntryTypes]:
        """Get the conversation history."""
        return self.entries

    def set(self, entries: Sequence[ConversationEntryTypes]) -> "Conversation":
        """Returns a new conversation with the conversation history set."""
        return self.model_copy(update={"entries": entries})

    def to_messages(self) -> list[dict[str, Any]]:
        """Convert the conversation to a list of dictionaries."""
        return [message.model_dump() for message in self.entries]

    def merge(self, conversation: "Conversation") -> "Conversation":
        """Returns a new conversation with the conversation history merged."""
        return self.model_copy(update={"entries": [*self.entries, *conversation.entries]})

    def count_tokens(self) -> int:
        """Count the number of tokens in the conversation."""
        return sum(
            entry.token_usage
            for entry in self.entries  # linter
            if isinstance(entry, AssistantConversationEntry) and entry.token_usage is not None
        )
