"""LiteLLM integration for FastMCP Agents."""

import json
from collections.abc import Sequence
from copy import deepcopy
from logging import Logger
from typing import Any, ClassVar, Literal, override

from fastmcp.tools import Tool as FastMCPTool
from litellm import CustomStreamWrapper, LiteLLM, acompletion  # pyright: ignore[reportUnknownVariableType]
from litellm.types.utils import Function, Message, ModelResponse, StreamingChoices
from litellm.utils import supports_function_calling, supports_reasoning
from openai.types.chat import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastmcp_agents.util.logging import BASE_LOGGER
from fastmcp_agents.conversation.types import AssistantConversationEntry, Conversation, ToolRequestPart
from fastmcp_agents.errors.base import NoResponseError, UnknownToolCallError, UnsupportedFeatureError
from fastmcp_agents.errors.llm_link import ModelDoesNotSupportFunctionCallingError, ModelDoesNotSupportThinkingError
from fastmcp_agents.llm_link.base import (
    BaseLLMLink,
    CompletionMetadata,
    TokenCounter,
)


class LiteLLMCompletionSettings(BaseSettings):
    """Settings for Litellm completion."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="LITELLM_COMPLETION_", env_nested_delimiter="_", env_nested_max_split=1, use_attribute_docstrings=True
    )

    kwargs: dict[str, Any] = Field(default_factory=dict)
    """Extra kwargs to pass to the Litellm client. Provided in the format of LITELLM_COMPLETION_KWARGS_<KEY>=<VALUE>."""


class LiteLLMSettings(BaseSettings):
    """Settings for LLM links."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(use_attribute_docstrings=True)

    model: str = Field(default=...)
    """The model to use."""

    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    """The temperature to use."""

    reasoning_effort: Literal["low", "medium", "high"] | None = Field(default=None)
    """The reasoning effort to use."""

    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    """The presence penalty to use."""

    completion_settings: LiteLLMCompletionSettings = Field(default_factory=LiteLLMCompletionSettings)

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str | None) -> str | None:
        """Validate the model."""
        if v is None:
            msg = "Model is required for Litellm"
            raise ValueError(msg)
        return v


class LitellmLLMLink(BaseLLMLink):
    """Litellm LLM link."""

    client: LiteLLM

    settings: LiteLLMSettings

    token_usage: TokenCounter

    logger: Logger

    def __init__(
        self,
        client: LiteLLM | None = None,
        settings: LiteLLMSettings | None = None,
        logger: Logger | None = None,
        **kwargs: Any,  # pyright: ignore[reportAny]
    ):
        self.client = client or LiteLLM()

        self.logger = logger or BASE_LOGGER.getChild(__name__)

        self.settings = settings or LiteLLMSettings()

        self.token_usage = TokenCounter()

        super().__init__(logger=logger, **kwargs)

        self.validate_function_calling()
        self.validate_thinking()

    def validate_function_calling(self):
        """Validate that the model is a valid Litellm model and that it supports function calling"""
        model = self.settings.model

        if not supports_function_calling(model=model):
            raise ModelDoesNotSupportFunctionCallingError(model=model)

    def validate_thinking(self):
        """Validate that the model is a valid Litellm model and that it supports function calling"""
        model = self.settings.model

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
            raise NoResponseError(missing_item="tool calls", model=self.settings.model)

        self.logger.debug(f"Response contains {len(tool_calls)} tool requests: {tool_calls}")

        tool_call_requests: list[ToolRequestPart] = []

        for tool_call in tool_calls:
            tool_call_function: Function = tool_call.function

            if not tool_call_function.name:
                raise UnknownToolCallError(tool_name="unknown", extra_info=f"Tool call has no name: {tool_call}")

            cast_arguments: dict[str, Any] = json.loads(tool_call_function.arguments) or {}

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
            raise NoResponseError(missing_item="choices", model=self.settings.model)

        if not (choice := choices[0]):
            raise NoResponseError(missing_item="choice", model=self.settings.model)

        if isinstance(choice, StreamingChoices):
            raise UnsupportedFeatureError(feature="streaming completions")

        if not (chosen_message := choice.message):
            raise NoResponseError(missing_item="response message", model=self.settings.model)

        return chosen_message

    async def _extract_tool_call_requests(self, response: ModelResponse) -> list[ToolRequestPart]:
        """Extract the tool calls from the response.

        Returns:
            A list of tool call requests.
        """

        message = self._extract_message(response)

        return self._extract_tool_calls(message)

    @override
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
            model=self.settings.model,
            temperature=self.settings.temperature,
            reasoning_effort=self.settings.reasoning_effort,
            presence_penalty=self.settings.presence_penalty,
            tool_choice="required",
            timeout=120,
            tools=litellm_tools,
            num_retries=3,
            **self.settings.completion_settings.kwargs,  # pyright: ignore[reportAny]
        )

        # Make the typechecker happy
        if isinstance(model_response, CustomStreamWrapper):
            raise UnsupportedFeatureError(feature="streaming completions")

        completion_metadata = CompletionMetadata.from_model_extra(model_response.model_extra)
        self.token_usage.usage += completion_metadata.token_usage or 0

        message = self._extract_message(model_response)

        tool_call_requests = self._extract_tool_calls(message)

        return AssistantConversationEntry(role="assistant", tool_calls=tool_call_requests, token_usage=completion_metadata.token_usage)


def transform_fastmcp_tool_to_openai_tool(fastmcp_tool: FastMCPTool) -> ChatCompletionToolParam:
    """Convert an FastMCP tool to an OpenAI tool."""

    tool_name = fastmcp_tool.name
    tool_description = fastmcp_tool.description or ""
    tool_parameters = deepcopy(fastmcp_tool.parameters)

    return ChatCompletionToolParam(
        type="function",
        function=FunctionDefinition(
            name=tool_name,
            description=tool_description,
            parameters=tool_parameters,
            strict=False,
        ),
    )
