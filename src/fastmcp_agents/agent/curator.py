"""FastMCP Agent implementation."""


from fastmcp import Context
from fastmcp.exceptions import ToolError
from fastmcp.tools import Tool as FastMCPTool
from fastmcp.tools.tool import FunctionTool
from pydantic import Field

from fastmcp_agents.agent.multi_step import (
    DefaultErrorResponseModel,
    DefaultSuccessResponseModel,
    MultiStepAgent,
)
from fastmcp_agents.conversation.types import Conversation, UserConversationEntry
from fastmcp_agents.conversation.utils import build_conversation
from fastmcp_agents.llm_link.litellm import LitellmLLMLink

CURATOR_SYSTEM_PROMPT = """
You are a Tool curator called `{name}` that is embedded into a FastMCP Server. You act as an
interface between the remote user/agent and the tools available on the server.

You are described as:
```markdown
{description}
```

You should plan for which calls you can do in parallel (multiple in a single request) and which
you should do sequentially (one tool call per request). You should avoid calling more than 10 tools
in a single request.

When you are done, you should call the `report_task_success` tool with the result of the task.
If you are unable to complete the task, you should call the `report_task_failure` tool with the
reason you are unable to complete the task.

You are given instructions and a task and you must perform the task using the tools available to you.
Your tasks may be phrased in the form of `tell {name} to <task>` or just `<task>`.
"""


class CuratorAgent(MultiStepAgent):
    """An Agent that uses the tools available on the server to complete a requested task."""

    system_prompt: str = Field(default=CURATOR_SYSTEM_PROMPT)
    """The system prompt to use."""

    instructions: list[UserConversationEntry] | UserConversationEntry | str | None = Field(default=None)
    """The instructions to use."""

    def _build_conversation(self, task: str) -> Conversation:
        """Builds a conversation for the Curator Agent."""
        return build_conversation(
            system_prompt=self.system_prompt.format(name=self.name, description=self.description),
            instructions=self.instructions,
            task=task,
        )

    async def perform_task(
        self, task: str, ctx: Context | None = None
    ) -> tuple[Conversation, DefaultSuccessResponseModel | DefaultErrorResponseModel]:
        """Performs a task using the Curator Agent's default instructions and returns the conversation."""
        conversation = self._build_conversation(task=task)

        conversation, response = await self.run_steps(ctx=ctx, conversation=conversation)

        return conversation, response

    async def perform_task_return_result(self, task: str, ctx: Context | None = None) -> str:
        """Performs a task using the Agent's default instructions.

        Args:
            task: The task to perform.
        """

        _, result = await self.perform_task(ctx=ctx, task=task)

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


class CuratorTool(FunctionTool):
    """A tool that allows the Curator Agent to perform a task."""

    agent: CuratorAgent = Field(exclude=True)

    @classmethod
    def from_tools(
        cls,
        name: str,
        description: str,
        instructions: str,
        tools: list[FastMCPTool],
        system_prompt: str | None = None,
    ) -> FunctionTool:
        """Create a tool from an agent."""
        curator_agent = CuratorAgent(
            name=name,
            description=description,
            default_tools=tools,
            instructions=instructions,
            system_prompt=system_prompt or CURATOR_SYSTEM_PROMPT,
            llm_link=LitellmLLMLink(),
        )

        return cls(
            fn=curator_agent.perform_task_return_result,
            name=name,
            parameters={
                "task": {
                    "type": "string",
                    "description": "The task to perform.",
                }
            },
            description=description,
            agent=curator_agent,
        )
