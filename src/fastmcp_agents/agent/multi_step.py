"""Base class for multi-step agents."""

from collections.abc import Sequence
from typing import ParamSpec, TypeVar

from fastmcp import Context
from fastmcp.tools import FunctionTool
from fastmcp.tools import Tool as FastMCPTool
from pydantic import BaseModel

from fastmcp_agents.agent.single_step import SingleStepAgent
from fastmcp_agents.conversation.memory.base import MemoryFactoryProtocol, MemoryProtocol
from fastmcp_agents.conversation.types import (
    AssistantConversationEntry,
    Conversation,
    UserConversationEntry,
)
from fastmcp_agents.errors.agent import NoResponseError, TaskFailureError

REQUEST_MODEL = TypeVar("REQUEST_MODEL", bound=BaseModel)

SUCCESS_RESPONSE_MODEL = TypeVar("SUCCESS_RESPONSE_MODEL", bound=BaseModel)
ERROR_RESPONSE_MODEL = TypeVar("ERROR_RESPONSE_MODEL", bound=BaseModel)

DEFAULT_STEP_LIMIT = 15
DEFAULT_MAX_PARALLEL_TOOL_CALLS = 5

P = ParamSpec("P")


class MultiStepAgent(SingleStepAgent):
    """A Multi-step agent that can be registered as a tool on a FastMCP server."""

    def __init__(
        self,
        *args,
        memory_factory: MemoryFactoryProtocol,
        max_parallel_tool_calls: int,
        step_limit: int,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.memory_factory = memory_factory
        self.max_parallel_tool_calls = max_parallel_tool_calls
        self.step_limit = step_limit

    async def run_steps(
        self,
        *args,  # noqa: ARG002
        ctx: Context,
        conversation: Conversation,
        tools: Sequence[FastMCPTool],
        step_limit: int,
        success_response_model: type[SUCCESS_RESPONSE_MODEL],
        error_response_model: type[ERROR_RESPONSE_MODEL],
        raise_on_error_response: bool = True,
        **kwargs,  # noqa: ARG002
    ) -> tuple[Conversation, SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL]:
        """Run the agent for a given number of steps.

        Args:
            ctx: The context of the agent.
            conversation: The conversation history to send to the LLM.
            tools: The tools to use. If None, the default tools will be used.
            step_limit: The maximum number of steps to perform.
            success_response_model: The model to use for the success response.
            error_response_model: The model to use for the error response.
            raise_on_error_response: Whether to raise an error if the agent fails.

        Returns:
            A tuple of the final conversation and the requested success or error response model.
        """

        # To be set by a callback function.
        result: SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL | None = None

        def report_success(**kwargs):
            """Report successful completion of the task."""
            nonlocal result
            result = success_response_model.model_validate(obj=kwargs)

        def report_error(**kwargs):
            """Report failure of the task."""
            nonlocal result
            result = error_response_model.model_validate(obj=kwargs)

        success_tool = FunctionTool(fn=report_success, name="report_success", parameters=success_response_model.model_json_schema())
        error_tool = FunctionTool(fn=report_error, name="report_error", parameters=error_response_model.model_json_schema())

        # Add our callback functions to the tools.
        available_tools = [*tools, success_tool, error_tool]

        for i in range(1, step_limit):
            self._logger.info(f"Running step {i} / {step_limit}")

            assistant_conversation_entry, tool_conversation_entries = await self.run_step(
                ctx=ctx,
                prompt=conversation,
                tools=available_tools,
                step_number=i,
                step_limit=step_limit,
            )

            # Add the assistant and tool conversation entries to the conversation.
            conversation = conversation.extend(
                entries=[assistant_conversation_entry, *tool_conversation_entries],
            )

            # If the result is set, return the conversation and the result.
            if result is not None:
                if raise_on_error_response and isinstance(result, error_response_model):
                    raise TaskFailureError(self.name, result)

                return conversation, result

        # Agent failed to record a success or failure response within the step limit.
        raise NoResponseError(agent_name=self.name)

    async def run(
        self,
        ctx: Context,
        task: str | Conversation,
        tools: Sequence[FastMCPTool],
        step_limit: int,
        success_response_model: type[SUCCESS_RESPONSE_MODEL],
        error_response_model: type[ERROR_RESPONSE_MODEL],
        raise_on_error_response: bool,
    ) -> tuple[Conversation, SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL]:
        """Run the agent.

        Args:
            ctx: The context of the FastMCP Request.
            instructions: The instructions to send to the LLM.
            tools: The tools to use. If None, the default tools will be used.
            step_limit: The maximum number of steps to perform.
            success_response_model: The model to use for the success response.
            error_response_model: The model to use for the error response.
            raise_on_error_response: Whether to raise an error if the agent fails.

        Returns:
            A tuple of the final conversation and the requested success or error response model.
        """

        memory: MemoryProtocol = self.memory_factory()

        conversation = self._prepare_conversation(memory, task)

        available_tools: Sequence[FastMCPTool] = tools or self.default_tools

        conversation, completion_result = await self.run_steps(
            ctx=ctx,
            conversation=conversation,
            tools=available_tools,
            step_limit=step_limit or self.step_limit,
            success_response_model=success_response_model,
            error_response_model=error_response_model,
            raise_on_error_response=raise_on_error_response,
        )

        memory.set(conversation)

        return conversation, completion_result

    def _log_total_token_usage(self, conversation: Conversation):
        """Log the total token usage for the conversation."""
        total_tokens = sum(entry.token_usage or 0 for entry in conversation.entries if isinstance(entry, AssistantConversationEntry))
        self._logger.info(f"Total token usage: {total_tokens}")

    def _prepare_conversation(self, memory: MemoryProtocol, task: str | Conversation) -> Conversation:
        """Prepare the conversation for the agent. Either by using the conversation history or the instructions."""

        conversation: Conversation = memory.get()

        # If there is no conversation history, use the system prompt.
        if len(conversation.entries) == 0:
            conversation = self._system_prompt

        # If the task is a string, convert it to a conversation entry.
        if isinstance(task, str):
            task = Conversation(entries=[UserConversationEntry(content=task)])

        # Merge the instructions with the conversation history.
        return conversation.merge(task)
