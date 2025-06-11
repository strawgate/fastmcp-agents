"""Base class for multi-step agents."""

from collections import Counter
from collections.abc import Sequence
from textwrap import dedent
from typing import ParamSpec, TypeAlias, TypeVar, overload

from fastmcp import Context
from fastmcp.tools import FunctionTool
from fastmcp.tools import Tool as FastMCPTool
from pydantic import BaseModel, Field

from fastmcp_agents.agent.single_step import SINGLE_STEP_SYSTEM_PROMPT, SingleStepAgent
from fastmcp_agents.conversation.types import Conversation, SystemConversationEntry, UserConversationEntry
from fastmcp_agents.conversation.utils import get_tool_calls_from_conversation
from fastmcp_agents.errors.agent import NoResponseError

REQUEST_MODEL = TypeVar("REQUEST_MODEL", bound=BaseModel)

SUCCESS_RESPONSE_MODEL = TypeVar("SUCCESS_RESPONSE_MODEL", bound=BaseModel)
ERROR_RESPONSE_MODEL = TypeVar("ERROR_RESPONSE_MODEL", bound=BaseModel)

DEFAULT_STEP_LIMIT = 15
DEFAULT_MAX_PARALLEL_TOOL_CALLS = 10

P = ParamSpec("P")

MULTI_STEP_SYSTEM_PROMPT = (
    SINGLE_STEP_SYSTEM_PROMPT
    + f"""
You should plan for which calls you can do in parallel (multiple in a single request) and which
you should do sequentially (one tool call per request). You should not call more than {DEFAULT_MAX_PARALLEL_TOOL_CALLS}
tools in a single request.

When you are done, you should call the `report_success` tool with the result of the task.
If you are unable to complete the task, you should call the `report_failure` tool with the
reason you are unable to complete the task.
"""
)


class DefaultErrorResponseModel(BaseModel):
    """A default error response model for the agent."""

    success: bool = Field(default=False)
    """Whether the agent was successful."""

    error: str = Field(...)
    """The error message if the agent failed. You must provide a string error message."""


class DefaultSuccessResponseModel(BaseModel):
    """A default success response model for the agent."""

    success: bool = Field(default=True)
    """Whether the agent was successful."""

    result: str = Field(...)
    """The result of the agent. You must provide a string result."""


DefaultResponseModelTypes: TypeAlias = DefaultErrorResponseModel | DefaultSuccessResponseModel


class MultiStepAgent(SingleStepAgent):
    """A Multi-step agent that can be registered as a tool on a FastMCP server."""

    # max_parallel_tool_calls: int = Field(default=DEFAULT_MAX_PARALLEL_TOOL_CALLS)
    # """The maximum number of tool calls to perform in parallel."""

    system_prompt: SystemConversationEntry | str = Field(default=MULTI_STEP_SYSTEM_PROMPT)
    """The system prompt to use."""

    step_limit: int = Field(default=DEFAULT_STEP_LIMIT)
    """The maximum number of steps to perform."""

    @overload
    async def run_steps(
        self,
        *args,
        ctx: Context,
        task: list[UserConversationEntry] | UserConversationEntry | str,
        conversation: Conversation | None = None,
        tools: Sequence[FastMCPTool] | None = None,
        step_limit: int = DEFAULT_STEP_LIMIT,
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
    ) -> tuple[Conversation, SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL]: ...

    @overload
    async def run_steps(
        self,
        *args,
        ctx: Context,
        conversation: Conversation,
        tools: Sequence[FastMCPTool],
        step_limit: int,
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
    ) -> tuple[Conversation, SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL]: ...

    async def run_steps(
        self,
        *args,  # noqa: ARG002
        ctx: Context,
        task: list[UserConversationEntry] | UserConversationEntry | str | None = None,
        conversation: Conversation | None = None,
        tools: Sequence[FastMCPTool] | None = None,
        step_limit: int = DEFAULT_STEP_LIMIT,
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
        **kwargs,  # noqa: ARG002
    ) -> tuple[Conversation, SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL]:
        """Run the agent for a given number of steps.

        Args:
            ctx: The context of the FastMCP request.
            task: The task to send to the LLM to solicit tool call requests.
            conversation: A conversation to continue from.
            tools: The tools to use. If None, the default tools will be used.
            step_limit: The maximum number of steps to perform.
            success_response_model: The model to use for the success response.
            error_response_model: The model to use for the error response.
            raise_on_error_response: Whether to raise an error if the agent fails.

        Returns:
            A tuple of the final conversation and the requested success or error response model.
        """

        # Use the conversation if provided, otherwise build a new one from the system prompt and instructions.
        new_conversation = self._prepare_conversation(
            conversation=conversation,
            task=task,
        )

        # To be set by a callback function.
        result: SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL | None = None

        def report_success(**kwargs):
            """Report successful completion of the task."""
            nonlocal result
            result = success_response_model.model_validate(obj=kwargs)

        def report_failure(**kwargs):
            """Report failure of the task."""
            nonlocal result
            result = error_response_model.model_validate(obj=kwargs)

        success_tool = FunctionTool(
            fn=report_success,
            name="report_success",
            description="Report successful completion of the task.",
            parameters=success_response_model.model_json_schema(),
        )
        error_tool = FunctionTool(
            fn=report_failure,
            name="report_failure",
            description="Report failure of the task.",
            parameters=error_response_model.model_json_schema(),
        )

        # Add our callback functions to the tools.
        available_tools = [*list(tools or self.default_tools), success_tool, error_tool]

        step_count = 0

        while step_count < step_limit:
            step_count += 1
            self.logger.info(f"Running step {step_count} / {step_limit}")

            new_conversation = await self.run_step(
                ctx=ctx,
                conversation=new_conversation,
                tools=available_tools,
                step_number=step_count,
                step_limit=step_limit,
            )

            if result is not None:
                break

            # If the result is set, return the conversation and the result.

        # Summarize the Agent's Tool Calls
        tool_calls = get_tool_calls_from_conversation(new_conversation)
        successful_calls = Counter(tool_call.name for tool_call in tool_calls if tool_call.success)
        failed_calls = Counter(tool_call.name for tool_call in tool_calls if not tool_call.success)

        tokens_used = new_conversation.count_tokens()
        self._tool_logger.info(
            dedent(
                f"""
                Performed {step_count} steps (Tokens {tokens_used}).
                Tool calls succeeded: {successful_calls.most_common()},
                Tool calls failed: {failed_calls.most_common()}
                """
            )
        )

        if result is not None:
            return new_conversation, result

        # Agent failed to record a success or failure response within the step limit.
        raise NoResponseError(agent_name=self.name)
