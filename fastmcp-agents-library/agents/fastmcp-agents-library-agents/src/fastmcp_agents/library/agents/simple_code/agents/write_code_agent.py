#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform simple code tasks.
"""

import os
from textwrap import dedent
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from pydantic_ai import ModelRetry
from pydantic_ai.agent import Agent
from pydantic_ai.tools import RunContext, ToolDefinition
from pydantic_ai.toolsets import AbstractToolset

from fastmcp_agents.library.agents.evaluator.agents import FailedEvaluation, SuccessfulEvaluation, evaluate_performance
from fastmcp_agents.library.agents.search.toolsets import web_search_toolset_func, web_search_toolset_instructions
from fastmcp_agents.library.agents.shared.models.code_base import BaseCodeBase
from fastmcp_agents.library.agents.shared.models.status import Failure
from fastmcp_agents.library.agents.simple_code.models import (
    CodeAgentResponse,
    CodeChange,
)
from fastmcp_agents.library.agents.simple_code.prompts import (
    EXPERT_SOFTWARE_ENGINEER,
    PRIOR_ART,
    READ_ONLY_FILESYSTEM_TOOLS,
    READ_WRITE_FILESYSTEM_TOOLS,
    RESPONSE_FORMAT,
    WRITING_CODE_TIPS,
)


class CodeAgentInput(BaseModel):
    """The input for the read code agent."""

    code_base: BaseCodeBase = Field(description="The code base to use for the Agent.")


async def force_agent_tools(ctx: RunContext[CodeAgentInput], tool_defs: list[ToolDefinition]) -> list[ToolDefinition] | None:  # pyright: ignore[reportUnusedParameter]  # noqa: ARG001
    """At certain steps, force the Agent to pick from a subset of the tools."""

    return tool_defs


class SelfCheck(BaseModel):
    """A self-check to ensure you have completed the task correctly."""

    consistent_style: Annotated[
        bool,
        Field(description="Whether you have personally verified that your changes are consistent with the style of the code base."),
    ]

    committed_changes: Annotated[
        bool,
        Field(description="Whether you have committed your changes to the code base."),
    ]

    updated_documentation: Annotated[
        bool,
        Field(description="Whether you have verified that all required documentation changes have been made."),
    ]

    updated_tests: Annotated[
        bool,
        Field(description="Whether you have verified that all required test changes have been made."),
    ]

    line_by_line_review: Annotated[
        bool,
        Field(description="Whether you have reviewed the code changes line by line to ensure they are accurate and complete."),
    ]

    double_checked: Annotated[
        bool,
        Field(description=("Whether you have personally verified that the findings and recommendations are accurate and complete.")),
    ]

    thorough: Annotated[
        Literal["very thorough", "thorough", "not thorough"],
        Field(description=("The level of thoroughness you used in your work addressing the requested task.")),
    ]

    def thorough_enough(self) -> bool:
        """Whether the self-check has passed."""
        return self.thorough == "very thorough"

    @property
    def passed(self) -> bool:
        """Whether the self-check has passed."""
        return all(
            [
                self.committed_changes,
                self.updated_documentation,
                self.consistent_style,
                self.updated_tests,
                self.line_by_line_review,
                self.double_checked,
            ]
        )

    # if not self_check.passed:
    #     msg = "You must pass all items in the self-check before reporting task completion."
    #     raise ModelRetry(msg)

    # if self_check.thorough_enough():
    #     msg = "You must be very thorough in your work to receive a high grade."
    #     raise ModelRetry(msg)

    # if ctx.retry == 0 and findings != len(ctx.deps.findings):
    #     msg = (
    #         "Thank you for calling the `final_result_report_task_complete` tool! "
    #         "Please call the `final_result_report_task_complete` tool again with the same arguments."
    #     )
    #     raise ModelRetry(msg)

    # performance: SuccessfulEvaluation | FailedEvaluation = await evaluate_performance(ctx)

    # if isinstance(performance, FailedEvaluation):
    #     raise ModelRetry(message=performance.instructions)

    # return ReadCodeAgentResult(
    #     tldr=tldr,
    #     findings=ctx.deps.findings,
    # )


async def report_task_complete(
    ctx: RunContext[CodeAgentInput],
    summary: Annotated[
        str, Field(description="A summary of the changes made by the Agent that could be used as the body of a pull request.")
    ],
    code_changes: Annotated[list[CodeChange], Field(description="The code changes that were made by the Agent.")],
    allow_uncommitted_changes: Annotated[bool, Field(description="Whether to allow uncommitted changes to the code base.")],
    self_check: SelfCheck,
) -> CodeAgentResponse:
    """Report that you have completed the task.  You may not call this tool alongside any other tools. You must finish all
    tool calling before calling this tool.

    You will be given a grade based on how your result fits with the tools you have called, their responses, and the original
    task description. If you have not completed the task or you have not actually performed the items you have indicated you
    performed, this will return a `ModelRetry` and you will receive a poor grade.
    """

    if not allow_uncommitted_changes and ctx.deps.code_base.is_dirty():
        raise ModelRetry(message="The code base is dirty. Did you remember to commit your changes before reporting completion?")

    if not self_check.thorough_enough():
        raise ModelRetry(message="You must be very thorough in your work to receive a high grade.")

    if not self_check.passed:
        raise ModelRetry(message="You must pass all items in the self-check before reporting task completion.")

    code_review_criteria = dedent("""
    You are an expert code review agent.

    All messages shared are from the actions taken by a junior developer. You are given a code diff, along with the history
    of the Agent who completed the task. In the history, you will see what the Agent was asked to do, what it did, and what the code
    diff is. You should use this information to provide a critical review of the code implementation.

    You refuse to accept bad fixes or shortcuts. You have a low tolerance for bad code and will not accept it. You find
    it unacceptable when Junior developers take shortcuts and do not fix the root cause of the problem.

    If there are flaws in the code implementation, you should report a failed evaluation with a list of flaws in the code
    implementation with specific actionable steps for the Agent to resolve the flaws. You should be thorough and an Agent
    following your comprehensive recommendations should not require further changes.

    If there are no required revisions, return "SuccessfulEvaluation".
    """)

    performance: SuccessfulEvaluation | FailedEvaluation = await evaluate_performance(ctx, additional_criteria=code_review_criteria)

    if isinstance(performance, FailedEvaluation):
        raise ModelRetry(message=performance.instructions)

    return CodeAgentResponse(summary=summary, code_diff=ctx.deps.code_base.diff(), code_changes=code_changes)


code_agent: Agent[CodeAgentInput, CodeAgentResponse | Failure] = Agent[CodeAgentInput, CodeAgentResponse | Failure](
    model=os.getenv("MODEL_CODE_IMPLEMENTATION_AGENT") or os.getenv("MODEL"),
    instructions=[
        EXPERT_SOFTWARE_ENGINEER,
        PRIOR_ART,
        READ_ONLY_FILESYSTEM_TOOLS,
        READ_WRITE_FILESYSTEM_TOOLS,
        WRITING_CODE_TIPS,
        RESPONSE_FORMAT,
    ],
    end_strategy="exhaustive",
    deps_type=CodeAgentInput,
    output_retries=5,
    output_type=[report_task_complete, Failure],
    prepare_tools=force_agent_tools,
)


@code_agent.toolset(per_run_step=False)
async def remote_repository_toolset(ctx: RunContext[CodeAgentInput]) -> AbstractToolset[CodeAgentInput]:  # pyright: ignore[reportUnusedParameter]
    return ctx.deps.code_base.to_toolset(read_only=False, git_tools=True)


code_agent.toolset(web_search_toolset_func)

code_agent.instructions(web_search_toolset_instructions)
