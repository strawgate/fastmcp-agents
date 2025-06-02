from typing import TypeAlias, TypeVar

from fastmcp import Context
from fastmcp.tools import Tool as FastMCPTool
from pydantic import BaseModel, Field

from fastmcp_agents.agent.single_step import SingleStepAgent
from fastmcp_agents.conversation.memory.base import MemoryFactoryProtocol
from fastmcp_agents.conversation.types import (
    AssistantConversationEntry,
    Conversation,
    UserConversationEntry,
)
from fastmcp_agents.conversation.utils import join_content
from fastmcp_agents.errors.agent import NoResponseError, TaskFailureError
from fastmcp_agents.llm_link.base import AsyncLLMLink

REQUEST_MODEL = TypeVar("REQUEST_MODEL", bound=BaseModel)

SUCCESS_RESPONSE_MODEL = TypeVar("SUCCESS_RESPONSE_MODEL", bound=BaseModel)
ERROR_RESPONSE_MODEL = TypeVar("ERROR_RESPONSE_MODEL", bound=BaseModel)

DEFAULT_STEP_LIMIT = 15
DEFAULT_MAX_PARALLEL_TOOL_CALLS = 5


class BaseResponseModel(BaseModel):
    pass


class DefaultErrorResponseModel(BaseResponseModel):
    error: str = Field(..., description="The error message if the agent failed. You must provide a string error message.")


class DefaultSuccessResponseModel(BaseResponseModel):
    success: bool = Field(..., description="Whether the agent was successful")
    result: str = Field(..., description="The result of the agent. You must provide a string result.")


class DefaultRequestModel(BaseModel):
    instructions: str = Field(..., description="The instructions for the agent")


DefaultResponseModelTypes: TypeAlias = DefaultErrorResponseModel | DefaultSuccessResponseModel


class MultiStepAgent(SingleStepAgent):
    """A Multi-step agent that can be registered as a tool on a FastMCP server."""

    def __init__(
        self,
        *,
        name: str,
        description: str,
        llm_link: AsyncLLMLink,
        system_prompt: str | Conversation,
        default_tools: list[FastMCPTool],
        memory_factory: MemoryFactoryProtocol,
        max_parallel_tool_calls: int,
        step_limit: int,
    ):
        super().__init__(
            name=name,
            description=description,
            system_prompt=system_prompt,
            llm_link=llm_link,
            default_tools=default_tools,
        )

        self.memory_factory = memory_factory
        self.max_parallel_tool_calls = max_parallel_tool_calls
        self.step_limit = step_limit

    def _log_state(self, conversation: Conversation) -> None:
        self._logger.info(f"Agent has {len(conversation.get())} entries in its conversation history")
        self._log_conversation_step(conversation)

    def _log_conversation_step(self, conversation: Conversation) -> None:
        previous_entry = conversation.get()[-2]
        previous_entry_content = previous_entry.content

        current_entry = conversation.get()[-1]
        current_entry_content = current_entry.content

        previous_content = previous_entry_content if isinstance(previous_entry_content, str) else join_content(previous_entry_content or [])
        current_content = current_entry_content if isinstance(current_entry_content, str) else join_content(current_entry_content or [])

        self._logger.info(f"Previous message: {previous_entry.role}: {previous_content[:200]}...")
        self._logger.info(f"Current message: {current_entry.role}: {current_content[:200]}...")

    async def run_step(
        self,
        ctx: Context,  # noqa: ARG002
        conversation: Conversation,
        tools: list[FastMCPTool],
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
    ) -> tuple[Conversation, SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL | None]:
        """Run a single step of the agent.

        This method is called to run a single step of the agent. It will:
        - Call the LLM
        - Handle the tool calls
        - Return the response

        Args:
            ctx: The context of the agent.
            conversation: The conversation history to send to the LLM.
            tools: The tools to use. If None, the default tools will be used.
            success_response_model: The model to use for the success response.
            error_response_model: The model to use for the error response.

        Returns:
            A tuple containing the conversation and the completion.
        """
        available_tools: list[FastMCPTool] = tools + self._completion_tools(success_response_model, error_response_model)

        conversation, tool_call_requests = await self._generate_tool_call_requests(conversation, available_tools)
        tool_names_requested = [tool_call_request.name for tool_call_request in tool_call_requests]

        if "report_task_success" in tool_names_requested:
            return conversation, success_response_model.model_validate(tool_call_requests[0].arguments)

        if "report_task_failure" in tool_names_requested:
            return conversation, error_response_model.model_validate(tool_call_requests[0].arguments)

        conversation = await self._perform_tool_call_requests(conversation, tool_call_requests, tools)

        return conversation, None

    async def run_interruption_step(
        self,
        ctx: Context,
        step_number: int,
        step_limit: int,
        conversation: Conversation,
        tools: list[FastMCPTool],
    ) -> Conversation:
        """Interrupt the running agent to alter the conversation, perform a task, or otherwise change the conversation.

        This method is called before each step of the agent.
        """

        if step_number % 5 == 0 and step_limit > 5:
            conversation = Conversation.add(
                conversation,
                AssistantConversationEntry(
                    content=f"I am on step {step_number} of {step_limit}. I have {step_limit - step_number} steps left. ",
                ),
            )

        return conversation

    async def run_steps(
        self,
        ctx: Context,
        conversation: Conversation,
        tools: list[FastMCPTool],
        step_limit: int = 10,
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
        raise_on_error_response: bool = True,
    ) -> tuple[Conversation, SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL | None]:
        """Run the agent for a given number of steps.

        Args:
            ctx: The context of the agent.
            conversation: The conversation history to send to the LLM.
            tools: The tools to use. If None, the default tools will be used.
            step_limit: The maximum number of steps to perform.
        """
        for i in range(1, step_limit):
            self._logger.info(f"Running step {i} / {step_limit}")

            # Interrupt the agent to alter the conversation, perform a task, or otherwise change the conversation.
            conversation = await self.run_interruption_step(ctx, i, step_limit, conversation, tools)

            conversation, completion_result = await self.run_step(ctx, conversation, tools, success_response_model, error_response_model)

            # LLM is tool calling -- continue to the next step
            if completion_result is None:
                continue

            self._logger.info(f"Completion: {completion_result.model_dump_json()[:200]}...")

            if raise_on_error_response and isinstance(completion_result, error_response_model):
                raise TaskFailureError(self.name, completion_result)

            return conversation, completion_result

        raise NoResponseError(self.name)

    async def run(
        self,
        ctx: Context,
        instructions: str | Conversation,
        tools: list[FastMCPTool] | None = None,
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
        raise_on_error_response: bool = True,
        step_limit: int = 10,
    ) -> tuple[Conversation, SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL]:
        """Run the agent.

        Args:
            ctx: The context of the agent.
            conversation: The conversation history to send to the LLM.
            step_limit: The maximum number of steps to perform.
            success_response_model: The model to use for the success response.
            error_response_model: The model to use for the error response.

        Returns:
            The requested success or error response model.
        """

        memory = self.memory_factory()

        if isinstance(instructions, str):
            instructions = Conversation(entries=[UserConversationEntry(content=instructions)])

        if len(memory.get()) == 0:
            conversation = Conversation.merge(self._system_prompt, instructions)
        else:
            conversation_history = Conversation(entries=memory.get())
            conversation = Conversation.merge(conversation_history, instructions)

        if tools is None:
            tools = self.default_tools

        available_tools: list[FastMCPTool] = tools

        self._log_state(conversation)

        conversation, completion_result = await self.run_steps(
            ctx, conversation, available_tools, step_limit, success_response_model, error_response_model, raise_on_error_response
        )

        return conversation, completion_result

    def get_system_prompt(self) -> Conversation:
        return self._system_prompt

    async def currate(self, ctx: Context, instructions: str) -> str:
        """Returns a function that can be used to invoke the current agent with instructions, default tools,
        a request model, and return a TaskFailureError or a text response to the caller.

        Useful for making the Agent available as a general purpose tool on the server.s
        """

        _, result = await self.run(
            ctx, instructions, success_response_model=DefaultSuccessResponseModel, error_response_model=DefaultErrorResponseModel
        )

        if isinstance(result, DefaultErrorResponseModel):
            raise TaskFailureError(self.name, result)

        return result.result

    @classmethod
    def _completion_tools(
        cls,
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
    ) -> list[FastMCPTool]:
        def _do_nothing() -> None:
            pass

        report_success = FastMCPTool(
            fn=_do_nothing,
            name="report_task_success",
            description="Report successful completion of the task.",
            parameters=success_response_model.model_json_schema(),
            annotations=None,
            serializer=None,
        )

        report_error = FastMCPTool(
            fn=_do_nothing,
            name="report_task_failure",
            description="Report failure of the task.",
            parameters=error_response_model.model_json_schema(),
            annotations=None,
            serializer=None,
        )

        return [report_success, report_error]
