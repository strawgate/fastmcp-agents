"""Pydantic models for conversation and tool calls."""

import json
from typing import Any, Literal, TypeAlias

from mcp.types import EmbeddedResource, ImageContent, TextContent
from openai.types.chat.chat_completion_message_tool_call_param import ChatCompletionMessageToolCallParam
from pydantic import BaseModel, Field, model_serializer

MCPToolResponseTypes = TextContent | ImageContent | EmbeddedResource


class CallToolRequest(BaseModel):
    """A helper class for a tool call request."""

    id: str = Field(
        ..., description="The id of the tool call request. This is used to match the tool call request to the tool call response."
    )
    name: str = Field(..., description="The name of the tool to call.")
    arguments: dict[str, Any] = Field(..., description="The arguments to pass to the tool.")

    @classmethod
    def from_openai(cls, message: ChatCompletionMessageToolCallParam) -> "CallToolRequest":
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


class CallToolResponse(BaseModel):
    """A helper class for a tool call response."""

    id: str = Field(
        ..., description="The id of the tool call request. This is used to match the tool call request to the tool call response."
    )
    name: str = Field(..., description="The name of the tool to call.")
    arguments: dict[str, Any] = Field(..., description="The arguments that were passed to the tool.", exclude=True)
    content: list[TextContent | ImageContent | EmbeddedResource] = Field(..., description="The content of the tool call response.")


class SystemConversationEntry(BaseModel):
    """A chat entry is a message in the chat history."""

    role: Literal["system"] = Field(default="system", description="A conversation entry that is a system message")
    content: str = Field(..., description="The content of the chat entry")


class UserConversationEntry(BaseModel):
    """A chat entry is a message in the chat history."""

    role: Literal["user"] = Field(default="user", description="A conversation entry that is a user message")
    content: str = Field(..., description="The content of the chat entry")


class ToolConversationEntry(BaseModel):
    """A tool call chat entry is a message in the chat history that is a tool call."""

    role: Literal["tool"] = Field(default="tool", description="A conversation entry that is a tool call")
    tool_call_id: str = Field(..., description="The id of the tool call request.")
    name: str = Field(..., description="The name of the tool to call.")
    content: list[TextContent | ImageContent | EmbeddedResource] = Field(..., description="The content of the tool call response.")

    @classmethod
    def from_tool_call_response(cls, tool_call_response: CallToolResponse) -> "ToolConversationEntry":
        return cls(
            role="tool",
            tool_call_id=tool_call_response.id,
            name=tool_call_response.name,
            content=tool_call_response.content,
        )


class AssistantConversationEntry(BaseModel):
    """A chat entry is a message in the chat history."""

    role: Literal["assistant"] = Field(default="assistant", description="A conversation entry that is an assistant message")
    content: str | None = Field(default=None, description="The content of the chat entry")
    tool_calls: list[CallToolRequest] = Field(default_factory=list, description="The tool calls that were made in the assistant message")
    token_usage: int | None = Field(default=None, description="The number of tokens used by the assistant message")


ConversationEntryTypes: TypeAlias = SystemConversationEntry | UserConversationEntry | AssistantConversationEntry | ToolConversationEntry


class Conversation(BaseModel):
    entries: list[ConversationEntryTypes] = Field(default_factory=list[ConversationEntryTypes], frozen=True)

    def append(self, message: ConversationEntryTypes) -> "Conversation":
        """Returns a new conversation with the message appended."""
        return self.model_copy(update={"entries": [*self.entries, message]})

    def extend(self, entries: list[ConversationEntryTypes]) -> "Conversation":
        """Returns a new conversation with the messages extended."""
        return self.model_copy(update={"entries": [*self.entries, *entries]})

    def get(self) -> list[ConversationEntryTypes]:
        """Get the conversation history."""
        return self.entries

    def set(self, entries: list[ConversationEntryTypes]) -> "Conversation":
        """Returns a new conversation with the conversation history set."""
        return self.model_copy(update={"entries": entries})

    def to_messages(self) -> list[dict[str, Any]]:
        """Convert the conversation to a list of dictionaries."""
        return [message.model_dump() for message in self.entries]

    def merge(self, conversation: "Conversation") -> "Conversation":
        """Returns a new conversation with the conversation history merged."""
        return self.model_copy(update={"entries": [*self.entries, *conversation.entries]})
