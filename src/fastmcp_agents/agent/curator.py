"""FastMCP Agent implementation."""

from fastmcp import Context
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from fastmcp_agents.agent.multi_step import (
    MULTI_STEP_SYSTEM_PROMPT,
    DefaultErrorResponseModel,
    DefaultSuccessResponseModel,
    MultiStepAgent,
)
from fastmcp_agents.conversation.types import Conversation, SystemConversationEntry, UserConversationEntry

CURATOR_SYSTEM_PROMPT = (
    MULTI_STEP_SYSTEM_PROMPT
    + """
You are a Tool curator that is embedded into a FastMCP Server. You act as an
interface between the remote user/agent and the tools available on the server.

If the task does not include specific instructions on what to include when reporting success,
you should report success with a breakdown of the steps or task you were asked to
complete and the steps you took to complete them.
"""
)


class TaskSuccess(BaseModel):
    """A success response model for the agent."""

    response: str = Field(..., description="The response to the task based on the instructions and task provided.")


class CuratorAgent(MultiStepAgent):
    """An Agent that uses the tools available on the server to complete a requested task."""

    system_prompt: SystemConversationEntry | str = Field(default=CURATOR_SYSTEM_PROMPT)
    """The system prompt to use."""

    async def perform_task_return_conversation(
        self, ctx: Context, task: str
    ) -> tuple[Conversation, DefaultSuccessResponseModel | DefaultErrorResponseModel]:
        """Performs a task using the Agent's default instructions and returns the conversation."""
        conversation, response = await self.run_steps(ctx=ctx, task=task)
        return conversation, response

    async def perform_task(self, ctx: Context, task: str) -> str:
        """Performs a task using the Agent's default instructions.

        Args:
            task: The task to perform.
        """

        _, result = await self.perform_task_return_conversation(ctx=ctx, task=task)

        if isinstance(result, DefaultSuccessResponseModel):
            return result.result

        raise ToolError(result.error)

    async def change_instructions(self, instructions: str):
        """Changes the Agent's instructions.

        Args:
            instructions: The instructions to use.
        """
        self.instructions = instructions

    async def get_instructions(self) -> str:
        """Gets the Agent's instructions."""
        if isinstance(self.instructions, str):
            return self.instructions

        if isinstance(self.instructions, UserConversationEntry):
            return self.instructions.content

        if isinstance(self.instructions, list):
            return str(self.instructions)

        msg = f"Invalid instructions type: {type(self.instructions)}"
        raise ValueError(msg)
