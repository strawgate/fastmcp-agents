"""FastMCP Agent implementation."""

from collections.abc import Sequence
from typing import TypeAlias

from fastmcp import Context
from fastmcp.tools import Tool as FastMCPTool
from pydantic import BaseModel, Field

from fastmcp_agents.agent.multi_step import ERROR_RESPONSE_MODEL, SUCCESS_RESPONSE_MODEL, MultiStepAgent
from fastmcp_agents.conversation.memory.base import MemoryFactoryProtocol, PrivateMemoryFactory
from fastmcp_agents.conversation.memory.ephemeral import EphemeralMemory
from fastmcp_agents.conversation.types import (
    Conversation,
    SystemConversationEntry,
)
from fastmcp_agents.errors.agent import TaskFailureError
from fastmcp_agents.llm_link.base import AsyncLLMLink
from fastmcp_agents.llm_link.litellm import AsyncLitellmLLMLink

DEFAULT_SYSTEM_PROMPT = """
You are `{agent_name}`, an AI Agent that is embedded into a FastMCP Server. You act as an
interface between the remote user/agent and the tools available on the server.

The person or Agent that invoked you understood received the following as a description of your capabilities:

````````markdown
{agent_description}
````````

You will be asked to perform a task. Your tasks will be phrased in the form of either `tell {agent_name} to <task>` or just `<task>`.
You should leverage the tools available to you to perform the task. You may perform many tool calls in one go but you should always
keep in mind that the tool calls may run in any order and may run at the same time. So you should plan
for which calls you can do in parallel (multiple in a single request) and which you should do sequentially (one tool call per request).
"""

DEFAULT_STEP_LIMIT = 20
"""The default step limit for the agent."""

DEFAULT_MAX_PARALLEL_TOOL_CALLS = 5
"""The default maximum number of tool calls to perform in parallel."""


class DefaultErrorResponseModel(BaseModel):
    """A default error response model for the agent."""

    error: str = Field(..., description="The error message if the agent failed. You must provide a string error message.")


class DefaultSuccessResponseModel(BaseModel):
    """A default success response model for the agent."""

    success: bool = Field(..., description="Whether the agent was successful")
    result: str = Field(..., description="The result of the agent. You must provide a string result.")


DefaultResponseModelTypes: TypeAlias = DefaultErrorResponseModel | DefaultSuccessResponseModel


class FastMCPAgent(MultiStepAgent):
    """A basic FastMCP Agent that can be used to perform tasks.

    This agent is a multi-step agent that can be used to perform tasks. It will use the provided LLM link to perform the tasks.
    It will also use the provided memory factory to store the conversation history.
    """

    def __init__(
        self,
        *,
        name: str,
        description: str,
        system_prompt: str | Conversation | None = None,
        default_tools: list[FastMCPTool] | None = None,
        llm_link: AsyncLLMLink | None = None,
        memory_factory: MemoryFactoryProtocol | None = None,
        max_parallel_tool_calls: int | None = None,
        step_limit: int | None = None,
        **kwargs,
    ):
        """Create a new FastMCP Agent.

        Args:
            name: The name of the agent.
            description: The description of the agent.
            instructions: The instructions for the agent.
            default_tools: The default tools to use. Defaults to an empty list.
            llm_link: The LLM link to use. Defaults to a Litellm LLM link.
            system_prompt: The system prompt to use. Defaults to a default system prompt.
            memory_factory: The memory factory to use. Defaults to a private memory factory.
            max_parallel_tool_calls: The maximum number of tool calls to perform in parallel. Defaults to 5.
            step_limit: The maximum number of steps to perform. Defaults to 10.
        """

        if system_prompt is None:
            system_prompt = DEFAULT_SYSTEM_PROMPT

        if isinstance(system_prompt, str):
            system_prompt = system_prompt.format(agent_name=name, agent_description=description)

            system_prompt = Conversation(entries=[SystemConversationEntry(content=system_prompt)])

        super().__init__(
            name=name,
            description=description,
            system_prompt=system_prompt,
            llm_link=llm_link or AsyncLitellmLLMLink(),
            default_tools=default_tools or [],
            memory_factory=memory_factory or PrivateMemoryFactory(memory_class=EphemeralMemory),
            max_parallel_tool_calls=max_parallel_tool_calls or DEFAULT_MAX_PARALLEL_TOOL_CALLS,
            step_limit=step_limit or DEFAULT_STEP_LIMIT,
            **kwargs,
        )

    async def run(
        self,
        ctx: Context,
        task: str | Conversation,
        tools: Sequence[FastMCPTool] | None = None,
        step_limit: int | None = None,
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
        raise_on_error_response: bool = True,
    ) -> tuple[Conversation, SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL]:
        return await super().run(
            ctx=ctx,
            task=task,
            tools=tools or [],
            step_limit=step_limit or DEFAULT_STEP_LIMIT,
            success_response_model=success_response_model,
            error_response_model=error_response_model,
            raise_on_error_response=raise_on_error_response,
        )

    async def currate(self, ctx: Context, task: str) -> str:
        """Runs the agent with the provided task and default tools, returning a string result or raising a TaskFailureError.

        Useful for making the Agent available as a general purpose tool on the server.s
        """

        _, result = await self.run(ctx, task, self.default_tools, self.step_limit)

        if isinstance(result, DefaultErrorResponseModel):
            raise TaskFailureError(self.name, result)

        return result.result
