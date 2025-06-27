"""LiteLLM integration for FastMCP Agents."""

import json
from collections.abc import Sequence
from typing import Any, Literal

from fastmcp.tools import Tool as FastMCPTool
from litellm import CustomStreamWrapper, LiteLLM, acompletion
from litellm.types.utils import ChatCompletionMessageToolCall, Function, Message, ModelResponse, StreamingChoices
from litellm.utils import supports_function_calling, supports_reasoning
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastmcp_agents.conversation.types import AssistantConversationEntry, Conversation, ToolRequestPart
from fastmcp_agents.errors.base import NoResponseError, UnknownToolCallError, UnsupportedFeatureError
from fastmcp_agents.errors.llm_link import ModelDoesNotSupportFunctionCallingError, ModelDoesNotSupportThinkingError
from fastmcp_agents.llm_link.base import (
    BaseLLMLink,
    CompletionMetadata,
    LLMLinkProtocol,
)
from fastmcp_agents.llm_link.utils import transform_fastmcp_tool_to_openai_tool


class LiteLLMSettings(BaseSettings):
    """Settings for LLM links."""

    model_config = SettingsConfigDict(
        env_prefix="LITELLM_", env_nested_delimiter="_", env_nested_max_split=1, use_attribute_docstrings=True
    )

    reasoning_effort: Literal["low", "medium", "high"] | None = Field(default=None)
    """The reasoning effort to use."""

    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    """The presence penalty to use."""

    completion_kwargs: dict[str, Any] = Field(default_factory=dict)
    """Extra kwargs to pass to the Litellm client. Provided in the format of LITELLM_COMPLETION_KWARGS_<KEY>=<VALUE>."""


class LitellmLLMLink(BaseLLMLink, LLMLinkProtocol):
    """Litellm LLM link."""

    client: LiteLLM = Field(default_factory=LiteLLM)
    litellm_settings: LiteLLMSettings = Field(default_factory=LiteLLMSettings)

    def __init_subclass__(cls, **kwargs):
        pass

    def model_post_init(self, __context: Any) -> None:
        """Post-initialize the Litellm LLM link."""
        self.validate_function_calling()
        self.validate_thinking()

    def validate_function_calling(self):
        """Validate that the model is a valid Litellm model and that it supports function calling"""
        model = self.llm_link_settings.model

        if not supports_function_calling(model=model):
            raise ModelDoesNotSupportFunctionCallingError(model=model)

    def validate_thinking(self):
        """Validate that the model is a valid Litellm model and that it supports function calling"""
        model = self.llm_link_settings.model

        if not supports_reasoning(model=model):
            raise ModelDoesNotSupportThinkingError(model=model)

    def _extract_tool_calls(self, message: Message) -> list[ToolRequestPart]:
        """Extract the tool calls from the message.

        Args:
            message: The message to extract the tool calls from.

        Returns:
            A list of tool calls.
        """
        if not (tool_calls := message.tool_calls):
            raise NoResponseError(missing_item="tool calls", model=self.llm_link_settings.model)

        self.logger.debug(f"Response contains {len(tool_calls)} tool requests: {tool_calls}")

        tool_call_requests: list[ToolRequestPart] = []

        for tool_call in tool_calls:
            if not isinstance(tool_call, ChatCompletionMessageToolCall):
                raise UnknownToolCallError(
                    tool_name=tool_call.name, extra_info=f"Tool call is not a ChatCompletionMessageToolCall: {tool_call}"
                )

            tool_call_function: Function = tool_call.function

            if not tool_call_function.name:
                raise UnknownToolCallError(tool_name="unknown", extra_info=f"Tool call has no name: {tool_call}")

            cast_arguments = json.loads(tool_call_function.arguments) or {}

            tool_call_requests.append(
                ToolRequestPart(
                    id=tool_call.id,
                    name=tool_call_function.name,
                    arguments=cast_arguments,
                )
            )

        return tool_call_requests

    def _extract_message(self, response: ModelResponse) -> Message:
        """Extract the response message from the response. This contains the tool_calls and content."""
        if not (choices := response.choices) or len(choices) == 0:
            raise NoResponseError(missing_item="choices", model=self.llm_link_settings.model)

        if not (choice := choices[0]):
            raise NoResponseError(missing_item="choice", model=self.llm_link_settings.model)

        if isinstance(choice, StreamingChoices):
            raise UnsupportedFeatureError(feature="streaming completions")

        if not (chosen_message := choice.message):
            raise NoResponseError(missing_item="response message", model=self.llm_link_settings.model)

        return chosen_message

    async def _extract_tool_call_requests(self, response: ModelResponse) -> list[ToolRequestPart]:
        """Extract the tool calls from the response.

        Returns:
            A list of tool call requests.
        """

        message = self._extract_message(response)

        return self._extract_tool_calls(message)

    async def async_completion(
        self,
        conversation: Conversation,
        fastmcp_tools: Sequence[FastMCPTool],
    ) -> AssistantConversationEntry:
        """Call the LLM with the given messages and tools.

        Args:
            conversation: The conversation to send to the LLM.
            tools: The tools to use.

        Returns:
            The assistant conversation entry.
        """

        litellm_tools = [transform_fastmcp_tool_to_openai_tool(tool) for tool in fastmcp_tools]

        messages = conversation.to_messages()

        model_response = await acompletion(
            messages=messages,
            model=self.llm_link_settings.model,
            temperature=self.llm_link_settings.temperature,
            reasoning_effort=self.litellm_settings.reasoning_effort,
            presence_penalty=self.litellm_settings.presence_penalty,
            **self.litellm_settings.completion_kwargs,
            tool_choice="required",
            timeout=120,
            tools=litellm_tools,
            num_retries=3,
        )

        # Make the typechecker happy
        if isinstance(model_response, CustomStreamWrapper):
            raise UnsupportedFeatureError(feature="streaming completions")

        completion_metadata = CompletionMetadata()
        if model_response.model_extra:
            token_usage = model_response.model_extra.get("usage", {}).get("total_tokens", 0)

            completion_metadata.token_usage = token_usage
            self.token_usage += token_usage

        message = self._extract_message(model_response)

        tool_call_requests = self._extract_tool_calls(message)

        return AssistantConversationEntry(role="assistant", tool_calls=tool_call_requests, token_usage=completion_metadata.token_usage)
