#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform simple code tasks.
"""

import os
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai.agent import Agent
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.tools import RunContext, ToolDefinition
from pydantic_ai.toolsets import AbstractToolset

from fastmcp_agents.library.agents.evaluator.agents import FailedEvaluation, SuccessfulEvaluation, evaluate_performance
from fastmcp_agents.library.agents.search.toolsets import web_search_toolset_func, web_search_toolset_instructions
from fastmcp_agents.library.agents.shared.models.code_base import BaseCodeBase
from fastmcp_agents.library.agents.shared.models.findings import (
    TLDR,
    CodeFinding,
    FindingDependency,
)
from fastmcp_agents.library.agents.shared.models.status import Failure
from fastmcp_agents.library.agents.simple_code.prompts import (
    EXPERT_SOFTWARE_ENGINEER,
    FINDINGS_AND_RECOMMENDATIONS,
    PRIOR_ART,
    READ_ONLY_FILESYSTEM_TOOLS,
    RESPONSE_FORMAT,
    SUGGESTING_CODE_TIPS,
)


class ReadCodeAgentInput(FindingDependency):
    """The input for the read code agent."""

    code_base: BaseCodeBase = Field(description="The code base to use for the Agent.")


async def force_agent_tools(ctx: RunContext[ReadCodeAgentInput], tool_defs: list[ToolDefinition]) -> list[ToolDefinition] | None:  # pyright: ignore[reportUnusedParameter]  # noqa: ARG001
    """At certain steps, force the Agent to pick from a subset of the tools."""

    return tool_defs


class ReadCodeAgentResult(BaseModel):
    """The result of the read code agent."""

    tldr: TLDR

    findings: list[CodeFinding] = Field(
        default=...,
        description="The findings the Agent identified while performing the task.",
    )


class SelfCheck(BaseModel):
    """A self-check to ensure you have completed the task correctly."""

    only_tool_call: Annotated[
        bool,
        Field(
            description=(
                "Whether this is the only tool call you are making right now and that you reported all findings and recommendations "
                "in previous steps."
            )
        ),
    ]

    findings_reported: Annotated[bool, Field(description="Whether you have reported all relevant findings via the add findings tools.")]

    consistent_style: Annotated[
        bool,
        Field(description="Whether you have personally verified that your recommendations are consistent with the style of the code base."),
    ]

    consistent_goals: Annotated[
        bool,
        Field(description="Whether you have personally verified that your recommendations are consistent with the goals of the code base."),
    ]

    consistent_approach: Annotated[
        bool,
        Field(
            description="Whether you have personally verified that your recommendations are consistent with the approach of the code base."
        ),
    ]

    double_checked: Annotated[
        bool,
        Field(description=("Whether you have personally verified that the findings and recommendations are accurate and complete.")),
    ]

    thorough: Annotated[
        Literal["very thorough", "thorough", "not thorough"],
        Field(description=("The level of thoroughness you used in your work addressing the requested task.")),
    ]

    @property
    def passed(self) -> bool:
        """Whether the self-check has passed."""
        return all(
            [
                self.findings_reported,
                self.only_tool_call,
                self.consistent_style,
                self.consistent_goals,
                self.consistent_approach,
                self.double_checked,
            ]
        )


async def report_task_complete(
    ctx: RunContext[ReadCodeAgentInput],
    tldr: TLDR,
    findings: Annotated[int, Field(description="The number of findings the Agent reported while performing the task.")],
    self_check: SelfCheck,
) -> ReadCodeAgentResult:
    """Report that you have completed the task.  You may not call this tool alongside any other tools. You must finish all
    tool calling before calling this tool.

    You will be given a grade based on how your result fits with the tools you have called, their responses, and the original
    task description. If you have not completed the task or you have not actually performed the items you have indicated you
    performed, this will return a `ModelRetry` and you will receive a poor grade.
    """

    if not self_check.passed:
        msg = "You must pass all items in the self-check before reporting task completion."
        raise ModelRetry(msg)

    if self_check.thorough != "very thorough":
        msg = "You must be very thorough in your work to receive a high grade."
        raise ModelRetry(msg)

    if ctx.retry == 0 and findings != len(ctx.deps.findings):
        msg = (
            "Thank you for calling the `final_result_report_task_complete` tool! "
            "Please call the `final_result_report_task_complete` tool again with the same arguments."
        )
        raise ModelRetry(msg)

    performance: SuccessfulEvaluation | FailedEvaluation = await evaluate_performance(ctx)

    if isinstance(performance, FailedEvaluation):
        raise ModelRetry(message=performance.instructions)

    return ReadCodeAgentResult(
        tldr=tldr,
        findings=ctx.deps.findings,
    )


read_code_agent: Agent[ReadCodeAgentInput, ReadCodeAgentResult | Failure] = Agent[ReadCodeAgentInput, ReadCodeAgentResult | Failure](
    model=os.getenv("MODEL_READ_CODE_AGENT") or os.getenv("MODEL"),
    instructions=[
        EXPERT_SOFTWARE_ENGINEER,
        PRIOR_ART,
        FINDINGS_AND_RECOMMENDATIONS,
        (
            "You cannot make any changes to the code base. You can read the code base, find files, search etc, but you cannot make any, "
            "run any tests, make changes via git commands, or make any changes to the code base. Your goal is to investigate the code base "
            "and provide a detailed report of your findings following the instructions provided by the user."
        ),
        READ_ONLY_FILESYSTEM_TOOLS,
        SUGGESTING_CODE_TIPS,
        RESPONSE_FORMAT,
    ],
    end_strategy="exhaustive",
    deps_type=ReadCodeAgentInput,
    output_type=[report_task_complete, Failure],
    output_retries=5,
    prepare_tools=force_agent_tools,
)

read_code_agent.toolset(web_search_toolset_func)

read_code_agent.instructions(web_search_toolset_instructions)


@read_code_agent.toolset(per_run_step=False)
async def remote_repository_toolset(ctx: RunContext[ReadCodeAgentInput]) -> AbstractToolset[ReadCodeAgentInput]:  # pyright: ignore[reportUnusedParameter]
    return ctx.deps.code_base.to_toolset(read_only=True, git_tools=True)


@read_code_agent.toolset(per_run_step=False)
async def findings_toolset(ctx: RunContext[ReadCodeAgentInput]) -> AbstractToolset[Any]:
    """Add a general finding to the list of findings."""
    return ctx.deps.to_findings_toolset()
