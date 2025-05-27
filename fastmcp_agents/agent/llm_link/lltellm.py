import json

from litellm import CustomStreamWrapper, LiteLLM, acompletion
from litellm.experimental_mcp_client.tools import transform_mcp_tool_to_openai_tool
from litellm.types.utils import ChatCompletionMessageToolCall, Function, Message, ModelResponse, StreamingChoices
from litellm.utils import supports_function_calling
from mcp.types import Tool as MCPTool

from fastmcp_agents.agent.errors.base import NoResponseError, UnknownToolCallError, UnsupportedFeatureError
from fastmcp_agents.agent.errors.llm_link import ModelDoesNotSupportFunctionCallingError
from fastmcp_agents.agent.llm_link.base import (
    AsyncLLMLink,
)
from fastmcp_agents.agent.types import AssistantConversationEntry, ToolCallRequest


class AsyncLitellmLLMLink(AsyncLLMLink):
    model: str

    def __init__(self, model: str, completion_kwargs: dict | None = None, client: LiteLLM | None = None) -> None:
        """Create a new Litellm LLM link.

        Args:
            model: The model to use.
            completion_kwargs: The completion kwargs to use.
            client: The Litellm client to use.
        """
        self.client = client or LiteLLM()

        self.model = model
        self.completion_kwargs = completion_kwargs or {}

        self.validate_model(model)

    @classmethod
    def validate_model(cls, model: str):
        """Validate that the model is a valid Litellm model and that it supports function calling

        Args:
            model: The model to validate.
        """
        # valid_models = get_valid_models()

        # if model not in valid_models:
        #     raise ModelDoesNotExistError(model=model)

        if not supports_function_calling(model=model):
            raise ModelDoesNotSupportFunctionCallingError(model=model)

    async def _extract_tool_calls(self, response: ModelResponse) -> tuple[Message, list[ToolCallRequest]]:
        """Extract the tool calls from the response.

        Args:
            response: The response from the LLM.

        Returns:
            A list of tool calls.
        """

        if not (choices := response.choices) or len(choices) == 0:
            raise NoResponseError(missing_item="choices", model=self.model)

        if len(choices) > 1:
            raise UnsupportedFeatureError(feature="completions returning multiple choices")

        if isinstance(choices[0], StreamingChoices):
            raise UnsupportedFeatureError(feature="streaming completions")

        choice = choices[0]

        if not (response_message := choice.message):
            raise NoResponseError(missing_item="response message", model=self.model)

        if not (tool_calls := response_message.tool_calls):
            raise NoResponseError(missing_item="tool calls", model=self.model)

        self.logger.debug(f"Response contains {len(tool_calls)} tool requests: {tool_calls}")

        tool_call_requests = []

        for tool_call in tool_calls:
            if not isinstance(tool_call, ChatCompletionMessageToolCall):
                raise UnknownToolCallError(
                    tool_name=tool_call.name, extra_info=f"Tool call is not a ChatCompletionMessageToolCall: {tool_call}"
                )

            tool_call_function: Function = tool_call.function

            if not tool_call_function.name:
                raise UnknownToolCallError(tool_name="unknown", extra_info=f"Tool call has no name: {tool_call}")

            cast_arguments = json.loads(tool_call_function.arguments) or {}

            tool_call_request = ToolCallRequest(
                id=tool_call.id,
                name=tool_call_function.name,
                arguments=cast_arguments,
            )

            tool_call_requests.append(tool_call_request)

        return response_message, tool_call_requests

    async def async_completion(
        self,
        messages: list,
        tools: list[MCPTool],
    ) -> tuple[AssistantConversationEntry, list[ToolCallRequest]]:
        """Call the LLM with the given messages and tools.

        Args:
            messages: The messages to send to the LLM.
            tools: The tools to use.
        """

        openai_tools = [transform_mcp_tool_to_openai_tool(tool) for tool in tools]

        model_response = await acompletion(
            messages=messages,
            model=self.model,
            **self.completion_kwargs,
            tools=openai_tools,
            tool_choice="required",
            num_retries=3
        )

        if isinstance(model_response, CustomStreamWrapper):
            raise UnsupportedFeatureError(feature="streaming completions")

        response_message, tool_call_requests = await self._extract_tool_calls(model_response)

        self.logger.debug(f"Tool call requests: {tool_call_requests}")
        self.logger.debug(f"Response message: {response_message}")

        return self._response_to_assistant_conversation_entry(response_message), tool_call_requests

    @classmethod
    def _response_to_assistant_conversation_entry(cls, response_message: Message) -> AssistantConversationEntry:
        """Convert a response message to an assistant conversation entry.

        Args:
            response_message: The response message to convert.
        """

        return AssistantConversationEntry(
            role="assistant",
            content=response_message.content or "",
            tool_calls=response_message.tool_calls or [],
        )


    @classmethod
    def from_litellm(cls, litellm: LiteLLM, model: str, completion_kwargs: dict | None = None):
        """Create a new Litellm LLM link from a Litellm client. Not normally needed.

        Args:
            litellm: The Litellm client to use.
            model: The model to use.
            completion_kwargs: The completion kwargs to use.

        Returns:
            A new Litellm LLM link.

        Example:
            >>> litellm = LiteLLM(api_key="your-api-key")
            >>> llm_link = AsyncLitellmLLMLink.from_litellm(litellm, model="gpt-4o-mini")
        """
        return cls(model=model, client=litellm, completion_kwargs=completion_kwargs)

    @classmethod
    def from_model(cls, model: str, completion_kwargs: dict | None = None):
        """Create a new Litellm LLM link from a model name.

        Args:
            model: The model to use.
            completion_kwargs: The completion kwargs to use.

        Returns:
            A new Litellm LLM link.

        Example:
            >>> llm_link = AsyncLitellmLLMLink.from_model(model="gpt-4o-mini")

        """
        litellm = LiteLLM()
        return cls(model=model, client=litellm, completion_kwargs=completion_kwargs)
