from typing import Any, Literal, TypeAlias

from mcp.types import EmbeddedResource, ImageContent, TextContent
from pydantic import BaseModel, Field


class DefaultRequestModel(BaseModel):
    instructions: str = Field(..., description="The instructions for the agent")


class BaseResponseModel(BaseModel):
    pass


class DefaultErrorResponseModel(BaseResponseModel):
    error: str = Field(..., description="The error message if the agent failed")


class DefaultSuccessResponseModel(BaseResponseModel):
    success: bool = Field(..., description="Whether the agent was successful")
    result: str = Field(..., description="The result of the agent")


DefaultResponseModelTypes: TypeAlias = DefaultErrorResponseModel | DefaultSuccessResponseModel


class SystemConversationEntry(BaseModel):
    """A chat entry is a message in the chat history."""

    role: Literal["system"] = Field(..., description="A conversation entry that is a system message")
    content: str = Field(..., description="The content of the chat entry")


class UserConversationEntry(BaseModel):
    """A chat entry is a message in the chat history."""

    role: Literal["user"] = Field(..., description="A conversation entry that is a user message")
    content: str = Field(..., description="The content of the chat entry")


class AssistantConversationEntry(BaseModel):
    """A chat entry is a message in the chat history."""

    role: Literal["assistant"] = Field(..., description="A conversation entry that is an assistant message")
    content: str = Field(..., description="The content of the chat entry")
    tool_calls: list = Field(..., description="The tool calls that were made in the assistant message")


class ToolCallChatEntry(BaseModel):
    """A tool call chat entry is a message in the chat history that is a tool call."""

    role: Literal["tool"] = Field(..., description="A conversation entry that is a tool call")
    tool_call_id: str = Field(..., description="The id of the tool call request.")
    name: str = Field(..., description="The name of the tool to call.")
    content: list[TextContent | ImageContent | EmbeddedResource] = Field(..., description="The content of the tool call response.")


ConversationEntryTypes: TypeAlias = SystemConversationEntry | UserConversationEntry | AssistantConversationEntry | ToolCallChatEntry


class ToolCallRequest(BaseModel):
    """A tool call request is a request to call a tool."""

    id: str = Field(
        ..., description="The id of the tool call request. This is used to match the tool call request to the tool call response."
    )
    name: str = Field(..., description="The name of the tool to call.")
    arguments: dict[str, Any] = Field(..., description="The arguments to pass to the tool.")


class PlanEntry(BaseModel):
    """A plan entry is a plan for the agent to follow."""

    tool: str = Field(..., description="The name of the tool I plan to call.")
    plan: str = Field(..., description="The plan for the agent to follow.")
    tool_calls: list[ToolCallRequest] = Field(..., description="The tool calls that were made in the plan.")


class PlanningResponse(BaseModel):
    """A planning response is a response to a planning request."""

    problem: str = Field(..., description="The problem the agent is trying to solve.")
    strategy: str = Field(..., description="The strategy for the agent to follow.")
    plan: list[PlanEntry] = Field(..., description="The plan for the agent to follow.")


# class DefaultResponseModel(BaseResponseModel):
#     error: DefaultErrorResponseModel | None = Field(default=None, description="The error message if the agent failed")
#     success: DefaultSuccessResponseModel | None = Field(default=None, description="Whether the agent was successful")

#     @model_validator(mode="after")
#     def validate_response(self):
#         if self.error and self.success:
#             raise ValueError("Cannot have both error and success")
#         if not self.error and not self.success:
#             raise ValueError("Must have either error or success")
#         return self
