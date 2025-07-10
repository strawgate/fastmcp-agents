"""Base class for multi-step agents."""

import logging
from collections import Counter
from collections.abc import Sequence
from textwrap import dedent
from time import time
from typing import Any, ClassVar, ParamSpec, Self, TypeVar

import yaml
from fastmcp import Context
from fastmcp.tools import FunctionTool
from fastmcp.tools import Tool as FastMCPTool
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent
from pydantic import BaseModel, Field, PrivateAttr, model_validator
from pydantic.config import ConfigDict

from fastmcp_agents.conversation.types import (
    AssistantConversationEntry,
    Conversation,
    ConversationEntryTypes,
    ToolConversationEntry,
    ToolRequestPart,
    UserConversationEntry,
)
from fastmcp_agents.conversation.utils import get_tool_calls_from_conversation
from fastmcp_agents.errors.agent import NoResponseError, ToolNotFoundError
from fastmcp_agents.llm_link.base import LLMLinkProtocol
from fastmcp_agents.util.base_model import StrictBaseModel
from fastmcp_agents.util.logging import BASE_LOGGER

logger = BASE_LOGGER

REQUEST_MODEL = TypeVar("REQUEST_MODEL", bound=BaseModel)

SUCCESS_RESPONSE_MODEL = TypeVar("SUCCESS_RESPONSE_MODEL", bound=BaseModel)
ERROR_RESPONSE_MODEL = TypeVar("ERROR_RESPONSE_MODEL", bound=BaseModel)

DEFAULT_STEP_LIMIT = 15
DEFAULT_MAX_PARALLEL_TOOL_CALLS = 10

P = ParamSpec("P")

# MULTI_STEP_SYSTEM_PROMPT = (
#     SINGLE_STEP_SYSTEM_PROMPT
#     + f"""
# You should plan for which calls you can do in parallel (multiple in a single request) and which
# you should do sequentially (one tool call per request). You should not call more than {DEFAULT_MAX_PARALLEL_TOOL_CALLS}
# tools in a single request.

# When you are done, you should call the `report_task_success` tool with the result of the task.
# If you are unable to complete the task, you should call the `report_task_failure` tool with the
# reason you are unable to complete the task.
# """
# )


class DefaultErrorResponseModel(StrictBaseModel):
    """A default error response model for the agent."""

    success: bool = Field(default=False)
    """Whether the agent was successful."""

    error: str = Field(...)
    """The error message if the agent failed. You must provide a string error message."""


class DefaultSuccessResponseModel(StrictBaseModel):
    """A default success response model for the agent."""

    success: bool = Field(default=True)
    """Whether the agent was successful."""

    result: str = Field(...)
    """The result of the agent. You must provide a string result."""


class MultiStepAgent(BaseModel):
    """A Multi-step agent that can be registered as a tool on a FastMCP server."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True, use_attribute_docstrings=True)

    name: str = Field(...)
    """The name of the agent."""

    description: str = Field(...)
    """The description of the agent."""

    # system_prompt: SystemConversationEntry | str = Field(default=SINGLE_STEP_SYSTEM_PROMPT)
    # """The system prompt to use."""

    # instructions: list[UserConversationEntry] | UserConversationEntry | str = Field(...)
    # """The instructions to use."""

    # system_prompt: SystemConversationEntry | str = Field(default=MULTI_STEP_SYSTEM_PROMPT)
    # """The system prompt to use."""

    default_tools: list[FastMCPTool] = Field(default_factory=list, exclude=True)
    """The default tools to use."""

    step_limit: int = Field(default=DEFAULT_STEP_LIMIT)
    """The maximum number of steps to perform."""

    llm_link: LLMLinkProtocol = Field(..., exclude=True)
    """The LLM link to use."""

    logger: logging.Logger = Field(default=BASE_LOGGER, exclude=True)
    """The logger to use."""

    _tool_logger: logging.Logger = PrivateAttr(default=BASE_LOGGER)
    """The logger to use for tool calls."""

    @model_validator(mode="after")
    def _validate_fields(self) -> Self:
        """Set the loggers."""

        self.logger = BASE_LOGGER.getChild(self.name)
        self._tool_logger = self.logger.getChild("tool")

        return self

    async def call_tool(
        self,
        tool_call_request: ToolRequestPart,
        fastmcp_tool: FastMCPTool,
    ) -> ToolConversationEntry:
        """Run a single tool call request with a single tool."""

        self._tool_logger.info(f"Calling tool {tool_call_request.name} with arguments {tool_call_request.arguments}")

        try:
            tool_response: ToolResult = await fastmcp_tool.run(arguments=tool_call_request.arguments)
            success = True
        except Exception as e:
            tool_response = ToolResult(content=[TextContent(type="text", text=f"Error calling tool {tool_call_request.name}: {e!s}")])
            success = False

        return ToolConversationEntry.from_tool_request_part(tool_call_request, tool_response, success)

    async def call_tools(
        self,
        tool_call_requests: list[ToolRequestPart],
        fastmcp_tools: Sequence[FastMCPTool] | None = None,
    ) -> list[ToolConversationEntry]:
        """Run a list of tool call requests with a list of tools.

        Args:
            tool_call_requests: The tool call requests to run.
            fastmcp_tools: The tools to use.

        Returns:
            The tool call responses.
        """

        tools_by_name = {tool.name: tool for tool in fastmcp_tools or self.default_tools}

        for tool_call_request in tool_call_requests:
            if tool_call_request.name not in tools_by_name:
                raise ToolNotFoundError(agent_name=self.name, tool_name=tool_call_request.name)

        self._tool_logger.info(f"Executing {len(tool_call_requests)} tool calls for agent.")

        tool_call_responses = [
            await self.call_tool(tool_call_request, tools_by_name[tool_call_request.name]) for tool_call_request in tool_call_requests
        ]

        self._log_call_tools(tool_call_requests, tool_call_responses)

        return tool_call_responses

    async def pick_tools(
        self,
        conversation: Conversation,
        tools: Sequence[FastMCPTool],
    ) -> AssistantConversationEntry:
        """Send the prompt to the LLM and ask it what tool calls it wants to make.

        Args:
            conversation: The conversation to send to the LLM to solicit tool call requests
            tools: The tools to use.

        Returns:
            A list of CallToolRequest objects.
        """

        assistant_conversation_entry = await self.llm_link.async_completion(conversation=conversation, fastmcp_tools=tools)

        self._log_pick_tools(assistant_conversation_entry)

        return assistant_conversation_entry

    async def run_step(
        self,
        *args: Any,  # pyright: ignore[reportAny, reportUnusedParameter]
        conversation: Conversation,
        tools: Sequence[FastMCPTool] | None = None,
        ctx: Context | None = None,  # pyright: ignore[reportUnusedParameter]
        **kwargs: Any,  # pyright: ignore[reportAny, reportUnusedParameter]
    ) -> Conversation:
        """Run a single step of the agent.

        This method is called to run a single step of the agent. It will:
        - Ask the LLM what tool calls it wants to make
        - Call the tools

        Args:
            ctx: The context of the FastMCP Request.
            conversation: A previous conversation to continue from.
            tools: The tools to use.

        Returns:
            The updated conversation.
        """

        # Pick the Tools
        assistant_conversation_entry = await self.pick_tools(conversation, tools or self.default_tools)

        # Call the Tools
        tool_conversation_entries = await self.call_tools(assistant_conversation_entry.tool_calls, tools)

        return conversation.extend(entries=[assistant_conversation_entry, *tool_conversation_entries])

    async def run_steps(
        self,
        *args: Any,  # pyright: ignore[reportAny, reportUnusedParameter]
        conversation: Conversation,
        tools: Sequence[FastMCPTool] | None = None,
        step_limit: int = DEFAULT_STEP_LIMIT,
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
        ctx: Context | None = None,
        **kwargs: Any,  # pyright: ignore[reportAny, reportUnusedParameter]
    ) -> tuple[Conversation, SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL]:
        """Run the agent for a given number of steps.

        Args:
            ctx: The context of the FastMCP request.
            conversation: A conversation to continue from.
            tools: The tools to use. If None, the default tools will be used.
            step_limit: The maximum number of steps to perform.
            success_response_model: The model to use for the success response.
            error_response_model: The model to use for the error response.
            raise_on_error_response: Whether to raise an error if the agent fails.

        Returns:
            A tuple of the final conversation and the requested success or error response model.
        """

        self._log_task(conversation)

        start_time = time()

        # To be set by a callback function.
        callback_result: SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL | None = None

        def report_task_success(**kwargs: Any):  # pyright: ignore[reportAny]
            nonlocal callback_result
            callback_result = success_response_model.model_validate(obj=kwargs)

        success_tool = FunctionTool(
            fn=report_task_success,
            name="report_task_success",
            description="When the task has been completed successfully, this tool allows reporting the successful result of the task.",
            parameters=success_response_model.model_json_schema(),
        )

        def report_task_failure(**kwargs: Any):  # pyright: ignore[reportAny]
            nonlocal callback_result
            callback_result = error_response_model.model_validate(obj=kwargs)

        error_tool = FunctionTool(
            fn=report_task_failure,
            name="report_task_failure",
            description="When the task is unable to be completed successfully, this tool allows reporting the failure of the task.",
            parameters=error_response_model.model_json_schema(),
        )

        step_count = 0

        while step_count < step_limit:
            step_count += 1
            tokens_msg = f"({conversation.count_tokens()} tokens consumed)" if conversation.count_tokens() > 0 else ""
            self.logger.info(f"Starting step {step_count} (Max steps: {step_limit}) of working on the task {tokens_msg}")

            conversation = await self.run_step(
                ctx=ctx,
                conversation=conversation,
                tools=[*list(tools or self.default_tools), success_tool, error_tool],
                step_number=step_count,
                step_limit=step_limit,
            )

            if callback_result:
                break  # pyright: ignore[reportUnreachable]

            # If the result is set, return the conversation and the result.
        self._log_run_steps_result(conversation, step_count, callback_result, start_time)

        if callback_result:
            return conversation, callback_result  # pyright: ignore[reportUnreachable]

        # Agent failed to record a success or failure response within the step limit.
        raise NoResponseError(agent_name=self.name)

    def _log_task(self, conversation: Conversation):
        """Log the task."""
        task: ConversationEntryTypes = conversation.entries[-1]

        if isinstance(task, UserConversationEntry):
            task_dict = {"task": task.content[:200]}
            self.logger.info(f"Received a task: {task_dict}")

    def _log_run_steps_result(self, conversation: Conversation, step_count: int, result: BaseModel | None, start_time: float):
        """Summarize the Agent's run."""
        tokens_used: int = conversation.count_tokens()

        duration: float = time() - start_time

        tool_calls: list[ToolConversationEntry] = get_tool_calls_from_conversation(conversation)

        failed_tool_calls: list[ToolConversationEntry] = [tool_call for tool_call in tool_calls if not tool_call.success]
        successful_tool_calls: list[ToolConversationEntry] = [tool_call for tool_call in tool_calls if tool_call.success]

        successful_call_counter: Counter[str] = Counter(tool_call.name for tool_call in successful_tool_calls)
        successful_call_count: dict[str, int] = dict(successful_call_counter.items())

        failed_call_counter: Counter[str] = Counter(tool_call.name for tool_call in failed_tool_calls)
        failed_call_count: dict[str, int] = dict(failed_call_counter.items())

        failed_call_summary: dict[str, str] = {
            tool_call.name: str(tool_call.content[0])[:100] for tool_call in failed_tool_calls if len(tool_call.content) > 0
        }

        message: str = dedent(
            f"""
            Agent is finished. Executed {len(tool_calls)} tool calls over {step_count} steps taking {duration:.2f}s.
            Tokens used: {tokens_used}
            Tool calls: {successful_call_count}
            """
        ).strip()

        if len(failed_tool_calls) > 0:
            message += f"\nFailed tool calls: {failed_call_count}"
            message += f"\nFailed tool call examples:\n{yaml.safe_dump(failed_call_summary, indent=2)}"

        self.logger.info(message)

        if result is not None:
            self.logger.info(f"Reporting Result: {result.model_dump(exclude_none=True)}")

    def _log_pick_tools(self, assistant_conversation_entry: AssistantConversationEntry):
        """Log the pick tools response."""

        tool_call_parts = [
            {tool_call_part.name: tool_call_part.arguments} if len(tool_call_part.arguments) > 0 else tool_call_part.name
            for tool_call_part in assistant_conversation_entry.tool_calls
        ]
        tokens: int | None = assistant_conversation_entry.token_usage

        tool_call_yaml: str = yaml.safe_dump(tool_call_parts, indent=2, sort_keys=False)
        self.logger.info(
            f"Needs {len(tool_call_parts)} tool calls ({tokens} tokens):\n{tool_call_yaml}".strip(),
        )

    def _log_call_tools(self, tool_call_requests: list[ToolRequestPart], conversation_entries: list[ToolConversationEntry]):
        """Log the call tools response."""

        tool_call_yaml: str = yaml.safe_dump([entry.to_loggable() for entry in conversation_entries], indent=2, sort_keys=False)
        self._tool_logger.info(f"Sharing {len(tool_call_requests)} tool call results:\n{tool_call_yaml}".strip())
