from collections.abc import Sequence
from typing import override

from fastmcp.tools.tool import FunctionTool
from fastmcp.tools.tool import Tool as FastMCPTool
from pydantic import BaseModel, Field, field_validator

from fastmcp_agents.core.agents.base import BaseMultiStepAgent, DefaultFailureModel, DefaultSuccessModel

TASK_AGENT_SYSTEM_PROMPT = """
You are a helpful Task Agent named `{name}` that has access to tools which can be leveraged to
answer questions and help with tasks. You work in a very supportive environment that values honesty and fairness.
You do not misrepresent your capabilities or your work, you just try to do your best.

You are described as:
```markdown
{description}
```

Your goal is to study the assigned task, gather the necessary information to properly understand the task, and then
produce a viable plan to complete the task. You will set clear, achievable goals to accomplish it. Prioritize these goals
in a logical order.

You can run many tool calls in a single step but you have a limited number of steps available to complete your task.
You will use the tools available to you to accomplish your goals.

If you are asked to do something that would require a tool, but you have no tools available, or it is clear that the tools
you do have available are not the ones required to complete the task, you will report failure.

When you have completed the task, you will report success.
"""


class TaskAgent(BaseMultiStepAgent):
    """A simple task agent that can be used to solve a task."""

    system_prompt: str = Field(
        default=TASK_AGENT_SYSTEM_PROMPT,
        description="The system prompt to use for the agent.",
    )

    instructions: str = Field(
        default=...,
        description="The instructions to use for the agent.",
    )

    @field_validator("instructions")
    @classmethod
    def validate_instructions(cls, v: list[str] | str | None) -> str | None:
        """Validate the instructions."""
        if isinstance(v, list):
            return "\n".join(v)
        return v

    @override
    def to_tool(self) -> FunctionTool:
        if not callable(self):
            self.__call__ = self.handle_task

        return FunctionTool.from_function(
            fn=self.__call__,  # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]
            name=self.name,
            description=self.description,
            tags=self.tags | {"agent"},
            enabled=self.enabled,
        )

    async def handle_task[SM: BaseModel, FM: BaseModel](
        self,
        *,
        task: str,
        tools: Sequence[FastMCPTool] | dict[str, FastMCPTool] | None = None,
        success_model: type[SM] = DefaultSuccessModel,
        failure_model: type[FM] = DefaultFailureModel,
    ) -> SM | FM:
        """Call the agent."""

        messages = [self.instructions, task] if self.instructions else [task]

        _, result = await self.run_steps(
            tools=tools or await self.get_tools(),
            messages=messages,
            success_model=success_model,
            failure_model=failure_model,
        )

        return result


# class GitCommitCount(BaseModel):
#     """The number of commits in the repository."""

#     count: int = Field(description="The number of commits in the repository.")


# class GitTaskAgent[SM: BaseModel = GitCommitCount, FM: BaseModel = DefaultFailureModel](TaskAgent):
#     """A task agent that can be used to run agents."""

#     system_prompt: str = Field(
#         default="You are a helpful task assistant that can answer questions and help with tasks.",
#         description="The system prompt to use for the agent.",
#     )

#     async def __call__(self, *, ctx: Context, repo: str, task: str) -> SM | FM:
#         """Call the agent."""

#         _, result = await self.run_steps(
#             ctx=ctx,
#             tools=await self.get_tools(ctx=ctx),
#             messages=[UserMessage(role="user", content=task)],
#         )

#         return result
