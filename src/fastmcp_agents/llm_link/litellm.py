"""LiteLLM integration for FastMCP Agents."""

import json
import os
from collections.abc import Sequence

from fastmcp.tools import Tool as FastMCPTool
from litellm import CustomStreamWrapper, LiteLLM, acompletion
from litellm.types.utils import ChatCompletionMessageToolCall, Function, Message, ModelResponse, StreamingChoices
from litellm.utils import supports_function_calling

from fastmcp_agents.conversation.types import AssistantConversationEntry, CallToolRequest, Conversation
from fastmcp_agents.errors.base import NoResponseError, UnknownToolCallError, UnsupportedFeatureError
from fastmcp_agents.errors.llm_link import ModelDoesNotSupportFunctionCallingError, ModelNotSetError
from fastmcp_agents.llm_link.base import (
    AsyncLLMLink,
    CompletionMetadata,
)
from fastmcp_agents.llm_link.utils import transform_fastmcp_tool_to_openai_tool


class AsyncLitellmLLMLink(AsyncLLMLink):
    model: str

    def __init__(self, model: str | None = None, completion_kwargs: dict | None = None, client: LiteLLM | None = None) -> None:
        """Create a new Litellm LLM link.

        Args:
            model: The model to use.
            completion_kwargs: The completion kwargs to use.
            client: The Litellm client to use.
        """
        self.client = client or LiteLLM()

        if model := (model or os.getenv("MODEL")):
            self.model = model
        else:
            raise ModelNotSetError

        self.completion_kwargs = completion_kwargs or {}

        self.validate_model(model)

    @classmethod
    def validate_model(cls, model: str):
        """Validate that the model is a valid Litellm model and that it supports function calling

        Args:
            model: The model to validate.
        """
        if not supports_function_calling(model=model):
            raise ModelDoesNotSupportFunctionCallingError(model=model)

    def _extract_tool_calls(self, message: Message) -> list[CallToolRequest]:
        """Extract the tool calls from the message.

        Args:
            message: The message to extract the tool calls from.

        Returns:
            A list of tool calls.
        """
        if not (tool_calls := message.tool_calls):
            raise NoResponseError(missing_item="tool calls", model=self.model)

        self.logger.debug(f"Response contains {len(tool_calls)} tool requests: {tool_calls}")

        tool_call_requests: list[CallToolRequest] = []

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
                CallToolRequest(
                    id=tool_call.id,
                    name=tool_call_function.name,
                    arguments=cast_arguments,
                )
            )

        return tool_call_requests

    def _extract_message(self, response: ModelResponse) -> Message:
        """Extract the response message from the response. This contains the tool_calls and content."""
        if not (choices := response.choices) or len(choices) == 0:
            raise NoResponseError(missing_item="choices", model=self.model)

        if not (choice := choices[0]):
            raise NoResponseError(missing_item="choice", model=self.model)

        if isinstance(choice, StreamingChoices):
            raise UnsupportedFeatureError(feature="streaming completions")

        if not (chosen_message := choice.message):
            raise NoResponseError(missing_item="response message", model=self.model)

        return chosen_message

    async def _extract_tool_call_requests(self, response: ModelResponse) -> list[CallToolRequest]:
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
            messages: The messages to send to the LLM.
            tools: The tools to use.

        Returns:
            The assistant conversation entry.
        """

        litellm_tools = [transform_fastmcp_tool_to_openai_tool(tool) for tool in fastmcp_tools]

        messages = conversation.to_messages()

        model_response = await acompletion(
            messages=messages,
            model=self.model,
            **self.completion_kwargs,
            tools=litellm_tools,
            tool_choice="required",
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
