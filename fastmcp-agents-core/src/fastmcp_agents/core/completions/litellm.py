from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any, override

from fastmcp.exceptions import ToolError
from fastmcp.tools import Tool
from fastmcp.tools.tool import ToolResult
from litellm import LiteLLM, acompletion  # pyright: ignore[reportUnknownVariableType]
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.types.completion import (
    ChatCompletionContentPartTextParam,
    # ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    # ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)
from litellm.types.llms.openai import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from litellm.types.utils import Choices, Message, ModelResponse, StreamingChoices
from mcp.types import (
    ContentBlock,
    TextContent,
)
from pydantic import TypeAdapter

from fastmcp_agents.core.completions.base import (
    BaseCompletionExtras,
    BasePendingToolCall,
    CompletionMessageType,
    LLMCompletionsProtocol,
)
from fastmcp_agents.core.completions.options import CompletionSettings

MESSAGE_PARAM_TYPE_ADAPTER: TypeAdapter[ChatCompletionMessageParam] = TypeAdapter(ChatCompletionMessageParam)

TOOL_ARGUMENTS_TYPE_ADAPTER: TypeAdapter[dict[str, Any]] = TypeAdapter(dict[str, Any])


class LiteLLMCompletionExtras(BaseCompletionExtras):
    """LiteLLM completion extras."""

    raw_token_usage: dict[str, Any] | None = None


class OpenAIPendingToolCall(BasePendingToolCall):
    tool_call_id: str

    @override
    def _tool_error_to_completion_message(self, tool_error: ToolError) -> ChatCompletionToolMessageParam:
        """Convert a tool error to a chat completion tool message."""

        return ChatCompletionToolMessageParam(
            role="tool",
            tool_call_id=self.tool_call_id,
            content=str(tool_error),
        )

    @override
    def _tool_result_to_completion_message(self, tool_result: ToolResult) -> ChatCompletionToolMessageParam:
        """Convert a tool result to a chat completion tool message."""

        content_parts: list[ChatCompletionContentPartTextParam] = []

        for content_block in tool_result.content:
            match content_block:
                case TextContent():
                    content_parts.append(ChatCompletionContentPartTextParam(type="text", text=content_block.text))
                case _:
                    msg = "Only TextContent is supported for tool results."
                    raise ValueError(msg)

        return ChatCompletionToolMessageParam(
            role="tool",
            tool_call_id=self.tool_call_id,
            content=content_parts,
        )


class LiteLLMCompletions(LLMCompletionsProtocol):
    """An implementation of the LLMCompletionsProtocol for OpenAI."""

    def __init__(self, default_model: str, client: LiteLLM | None = None, completion_settings: CompletionSettings | None = None) -> None:
        self.client: LiteLLM = client or LiteLLM()
        self.default_model: str = default_model
        self.completion_settings: CompletionSettings = completion_settings or CompletionSettings.from_environment()

    @override
    async def text(
        self,
        system_prompt: str,
        messages: Sequence[CompletionMessageType] | CompletionMessageType,
        **kwargs: Any,  # pyright: ignore[reportAny]
    ) -> tuple[LiteLLMCompletionExtras, CompletionMessageType, ContentBlock]:
        openai_messages = convert_messages_to_openai_messages(system_prompt, messages)

        model_response: ModelResponse | CustomStreamWrapper = await acompletion(
            model=self.default_model,
            messages=openai_messages,
            stream=False,
            temperature=self.completion_settings.temperature,
            max_tokens=self.completion_settings.max_tokens,
            top_p=self.completion_settings.top_p,
            frequency_penalty=self.completion_settings.frequency_penalty,
            reasoning_effort=self.completion_settings.reasoning_effort,
            **kwargs,  # pyright: ignore[reportAny]
        )

        completion = extract_completion(model_response=model_response)

        if isinstance(model_response, CustomStreamWrapper):
            msg = "Streaming is not supported for LiteLLM"
            raise NotImplementedError(msg)

        message = extract_first_choice_message(model_response)

        extras = get_extras(completion=completion, message=message)

        return extras, message.model_dump(), get_content_block_from_completion_message(message)

    async def _tools(
        self,
        system_prompt: str,
        messages: Sequence[CompletionMessageType] | CompletionMessageType,
        tools: Sequence[Tool] | dict[str, Tool],
        multiple_tool_calls: bool,
        **kwargs: Any,  # pyright: ignore[reportAny]
    ) -> tuple[LiteLLMCompletionExtras, CompletionMessageType, list[OpenAIPendingToolCall]]:
        openai_messages = convert_messages_to_openai_messages(system_prompt, messages)
        openai_tools = convert_fastmcp_tools_to_openai_tools(tools)

        model_response: ModelResponse | CustomStreamWrapper = await acompletion(
            model=self.default_model,
            messages=openai_messages,
            parallel_tool_calls=multiple_tool_calls,
            tools=openai_tools,
            tool_choice="required",
            stream=False,
            **kwargs,  # pyright: ignore[reportAny]
        )

        completion = extract_completion(model_response=model_response)

        assistant_message = extract_first_choice_message(model_response=model_response)

        pending_tool_calls = convert_chat_completion_message_to_pending_tool_calls(tools, assistant_message)

        extras = get_extras(completion=completion, message=assistant_message)

        return extras, assistant_message.model_dump(), pending_tool_calls

    @override
    async def tool(
        self,
        system_prompt: str,
        messages: Sequence[CompletionMessageType] | CompletionMessageType,
        tools: Sequence[Tool] | dict[str, Tool],
        **kwargs: Any,  # pyright: ignore[reportAny]
    ) -> tuple[LiteLLMCompletionExtras, CompletionMessageType, OpenAIPendingToolCall]:
        extras, assistant_message, pending_tool_calls = await self._tools(system_prompt, messages, tools, False, **kwargs)

        return extras, assistant_message, pending_tool_calls[0]

    @override
    async def tools(
        self,
        system_prompt: str,
        messages: Sequence[CompletionMessageType] | CompletionMessageType,
        tools: Sequence[Tool] | dict[str, Tool],
        **kwargs: Any,  # pyright: ignore[reportAny]
    ) -> tuple[LiteLLMCompletionExtras, CompletionMessageType, list[OpenAIPendingToolCall]]:
        return await self._tools(system_prompt, messages, tools, True, **kwargs)


def get_extras(completion: dict[str, Any], message: Message) -> LiteLLMCompletionExtras:
    """Get the extras from a LiteLLM completion."""

    extras: LiteLLMCompletionExtras = LiteLLMCompletionExtras(raw=completion)

    if usage := completion.get("usage"):
        extras.raw_token_usage = usage

        total_tokens: int | None = usage.get("total_tokens")
        if total_tokens:
            extras.token_usage = total_tokens

    if message.reasoning_content:
        extras.thinking = message.reasoning_content

    return extras


def extract_completion(model_response: ModelResponse | CustomStreamWrapper) -> dict[str, Any]:
    if isinstance(model_response, CustomStreamWrapper):
        msg = "Streaming is not supported for LiteLLM"
        raise NotImplementedError(msg)

    return model_response.model_dump()


def extract_thinking_from_message(message: Message | Mapping[str, Any]) -> str | None:
    """Extract the thinking from a message."""

    if isinstance(message, Mapping):
        message = Message(**message)  # pyright: ignore[reportAny]

    if not (reasoning_content := message.reasoning_content):
        return None

    return reasoning_content


def extract_first_choice_message(
    model_response: ModelResponse | CustomStreamWrapper,
) -> Message:
    """Extracts the first choice completion from a ChatCompletion."""

    if isinstance(model_response, CustomStreamWrapper):
        msg = "Streaming is not supported for LiteLLM"
        raise NotImplementedError(msg)

    if len(model_response.choices) == 0:
        msg = "No choices to pick from in the chat completion response."
        raise ValueError(msg)

    if len(model_response.choices) > 1:
        msg = "Multiple choices to pick from in the chat completion response."
        raise ValueError(msg)

    first_choice: Choices | StreamingChoices = model_response.choices[0]

    if isinstance(first_choice, StreamingChoices):
        msg = "Streaming is not supported for LiteLLM"
        raise NotImplementedError(msg)

    return first_choice.message


def convert_messages_to_openai_messages(
    system_prompt: str,
    messages: Sequence[CompletionMessageType] | CompletionMessageType,
) -> list[ChatCompletionMessageParam]:
    """Convert messages dictionaries to OpenAI Messages."""

    openai_messages: list[ChatCompletionMessageParam] = [ChatCompletionSystemMessageParam(role="system", content=system_prompt)]

    for message in messages:
        if isinstance(message, str):
            openai_messages.append(ChatCompletionUserMessageParam(role="user", content=message))
        else:
            openai_messages.append(MESSAGE_PARAM_TYPE_ADAPTER.validate_python(message))

    return openai_messages


def convert_chat_completion_message_to_pending_tool_calls(
    tools: Sequence[Tool] | dict[str, Tool],
    message: Message,
) -> list[OpenAIPendingToolCall]:
    """Converts the tool calls from a chat completion message to a list of pending tool calls.

    Args:
        tools: The list of tools to use for the tool calls.
        chat_completion_message: The chat completion message to create the pending tool calls from.

    Returns:
        A list of pending tool calls.
    """
    if not (tool_calls := message.tool_calls):
        msg = "No tool_call in the chat completion message."
        raise ValueError(msg)

    if isinstance(tools, dict):
        tools = list(tools.values())

    tools_by_name = {tool.name: tool for tool in tools}

    fastmcp_tool_calls: list[OpenAIPendingToolCall] = []

    for tool_call in tool_calls:
        if not (function_call := tool_call.function):
            msg = "No function call in the tool call."
            raise ValueError(msg)

        if not (tool_name := tool_call.function.name):
            msg = "No name in the function call of the tool call."
            raise ValueError(msg)

        if tool_name not in tools_by_name:
            msg = f"Tool {tool_name} not found in the list of tools."
            raise ValueError(msg)

        tool = tools_by_name[tool_name]

        fastmcp_tool_calls.append(
            OpenAIPendingToolCall(
                tool_call_id=tool_call.id,
                tool=tool,
                arguments=TOOL_ARGUMENTS_TYPE_ADAPTER.validate_json(function_call.arguments),
            )
        )

    return fastmcp_tool_calls


def convert_fastmcp_tools_to_openai_tools(
    fastmcp_tools: Sequence[Tool] | dict[str, Tool],
) -> list[ChatCompletionToolParam]:
    """Create a list of OpenAI Tool Definitions from a list of FastMCP Tools."""

    if isinstance(fastmcp_tools, dict):
        fastmcp_tools = list(fastmcp_tools.values())

    return [convert_fastmcp_tool_to_openai_tool(fastmcp_tool=tool) for tool in fastmcp_tools]


def convert_fastmcp_tool_to_openai_tool(
    fastmcp_tool: Tool,
) -> ChatCompletionToolParam:
    """Create an OpenAI Tool Definition from a FastMCP Tool."""

    tool_name = fastmcp_tool.name
    tool_description = fastmcp_tool.description or ""
    tool_parameters = deepcopy(fastmcp_tool.parameters)

    return ChatCompletionToolParam(
        type="function",
        function=ChatCompletionToolParamFunctionChunk(
            name=tool_name,
            description=tool_description,
            parameters=tool_parameters,
            strict=False,
        ),
    )


def get_content_block_from_completion_message(
    message: Message,
) -> ContentBlock:
    """Retrieves an MCP TextContent block from a chat completion."""

    if content := message.content:
        return TextContent(type="text", text=content)
    msg = "Only Text content is supported."
    raise ValueError(msg)


# def log_thinking_from_completion_message(
#     message: Message,
# ) -> None:
#     """Logs the thinking from a chat completion message."""

#     if reasoning_content := message.reasoning_content:
#         logger.info(reasoning_content)
