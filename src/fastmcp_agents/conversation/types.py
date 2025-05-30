from typing import Any, Literal, TypeAlias

from mcp.types import EmbeddedResource, ImageContent, TextContent
from pydantic import BaseModel, Field


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


class CallToolRequest(BaseModel):
    """A tool call request is a request to call a tool."""

    id: str = Field(
        ..., description="The id of the tool call request. This is used to match the tool call request to the tool call response."
    )
    name: str = Field(..., description="The name of the tool to call.")
    arguments: dict[str, Any] = Field(..., description="The arguments to pass to the tool.")


class CallToolResponse(BaseModel):
    """A tool call response is a response to a tool call request."""

    id: str = Field(
        ..., description="The id of the tool call request. This is used to match the tool call request to the tool call response."
    )
    name: str = Field(..., description="The name of the tool to call.")
    content: list[TextContent | ImageContent | EmbeddedResource] = Field(..., description="The content of the tool call response.")


class AssistantConversationEntry(BaseModel):
    """A chat entry is a message in the chat history."""

    role: Literal["assistant"] = Field(default="assistant", description="A conversation entry that is an assistant message")
    content: str | None = Field(default=None, description="The content of the chat entry")
    tool_calls: list = Field(default_factory=list, description="The tool calls that were made in the assistant message")


ConversationEntryTypes: TypeAlias = SystemConversationEntry | UserConversationEntry | AssistantConversationEntry | ToolConversationEntry


class Conversation(BaseModel):
    entries: list[ConversationEntryTypes] = Field(default_factory=list[ConversationEntryTypes], frozen=True)

    def add(self, message: ConversationEntryTypes) -> "Conversation":
        return self.model_copy(update={"entries": [*self.entries, message]})

    def get(self) -> list[ConversationEntryTypes]:
        return self.entries

    def set(self, entries: list[ConversationEntryTypes]) -> "Conversation":
        return self.model_copy(update={"entries": entries})

    def to_messages(self) -> list[dict[str, Any]]:
        return [message.model_dump() for message in self.entries]

    @classmethod
    def merge(cls, *conversations: "Conversation") -> "Conversation":
        return cls(entries=[entry for conversation in conversations for entry in conversation.entries])
