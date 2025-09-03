#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform GitHub tasks.
"""

import os
from typing import TYPE_CHECKING, Any, ClassVar

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic.type_adapter import TypeAdapter
from pydantic_ai import RunContext
from pydantic_ai.agent import Agent
from pydantic_ai.messages import ModelMessage

if TYPE_CHECKING:
    from pydantic_ai.run import AgentRunResult

PERSONA = """
## Persona
You are a Judge! Congratulations on your accomplishment. You are tasked with evaluating the performance of another AI Agent to
determine whether the Agent has completed the task and whether it has done so correctly.
"""

EVALUATOR_INSTRUCTIONS = """
## Evaluator Instructions
You have one goal: review the task, tool calls, and tool call responses to determine whether the Agent did what it said it did
or whether it made up information or lied about what it did.
"""

DEFAULT_CRITERIA = """
## Does the response match the task?
Evaluate the task on the final result and determine if the final result is a relevant, complete, and accurate response to the task.
Providing an incomplete or inaccurate response must result in a failed evaluation. If the task was not possible to complete, the
evaluation can succeed only if the Agent clearly indicates that the task was not possible to complete.

## Is the response well grounded?
Ensure that each item of the final result is based off of information gathered during a "tool call" or from the "user prompt".
The Agent may not fabricate information. This will most commonly occur after a tool call failure. If the Agent fabricates information,
you will point out the specific piece of fabricated information to the Agent.

## Did the Agent lie about what it did?
The Agent may not lie about what it did. For example, if the Agent indicates that it executed tests for a code change, did the Agent
actually execute the tests? If the Agent lies about what it did, you will point out the specific piece of information that
the Agent falsified.

## Remediation Instructions
Whenever possible, provide specific and actionable remediation instructions to the Agent. These remediation instructions, if followed,
should be enough for the Agent to pass the next evaluation.
"""


class EvaluatorAgentDependency(BaseModel):
    """A dependency for the GitHub Research Agent."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    messages: list[ModelMessage] = Field(description="The messages to evaluate.")

    task: str = Field(description="The task to evaluate the model's performance on.")

    criteria: str = Field(default=DEFAULT_CRITERIA, description="The criteria to evaluate the model's performance on.")


class EvaluatorAgentInput(EvaluatorAgentDependency):
    @classmethod
    def from_ctx(
        cls, ctx: RunContext[Any], base_criteria: str | None = None, additional_criteria: str | None = None
    ) -> "EvaluatorAgentInput":
        task = yaml.safe_dump(ctx.prompt)
        return cls(
            messages=ctx.messages,
            task=task,
            criteria=base_criteria or DEFAULT_CRITERIA + "\n\n" + (additional_criteria or ""),
        )

    def to_deps(self) -> EvaluatorAgentDependency:
        return EvaluatorAgentDependency(
            messages=self.messages,
            task=self.task,
            criteria=self.criteria,
        )


class SuccessfulEvaluation(BaseModel):
    """A result from the evaluation."""

    passed: bool = Field(description="Whether the Agent passed the evaluation.")


class FailedEvaluation(BaseModel):
    """A result from the evaluation."""

    passed: bool = Field(description="Whether the Agent passed the evaluation.")
    reason: str = Field(description="The reason the Agent passed or failed the evaluation.")
    instructions: str = Field(description="Instructions to provide to the Agent to help it achieve success.")


evaluator_agent: Agent[EvaluatorAgentDependency, SuccessfulEvaluation | FailedEvaluation] = Agent[
    EvaluatorAgentDependency, SuccessfulEvaluation | FailedEvaluation
](
    name="evaluator-agent",
    model=os.getenv("MODEL_EVALUATOR_AGENT") or os.getenv("MODEL"),
    instructions=[
        PERSONA,
        EVALUATOR_INSTRUCTIONS,
    ],
    deps_type=EvaluatorAgentDependency,
    output_type=[SuccessfulEvaluation, FailedEvaluation],
)


async def evaluate_performance(
    ctx: RunContext[Any], base_criteria: str | None = None, additional_criteria: str | None = None
) -> SuccessfulEvaluation | FailedEvaluation:
    """Evaluate the performance of the Agent."""

    evaluator_input = EvaluatorAgentInput.from_ctx(
        ctx=ctx,
        base_criteria=base_criteria,
        additional_criteria=additional_criteria,
    )

    agent_run_result: AgentRunResult[SuccessfulEvaluation | FailedEvaluation] = await evaluator_agent.run(deps=evaluator_input.to_deps())

    return agent_run_result.output


REMOVE_MESSAGE_KEYS = ["instructions", "usage", "model_name", "timestamp", "provider_details", "provider_request_id"]


@evaluator_agent.instructions
async def evaluator_agent_instructions(ctx: RunContext[EvaluatorAgentDependency]) -> str:
    """Instructions for the evaluator agent."""

    message_dump = TypeAdapter(list[ModelMessage]).dump_python(ctx.deps.messages)

    for message in message_dump:
        for key in REMOVE_MESSAGE_KEYS:
            if key in message:
                del message[key]

    return f"""
    ## Original Task
    {ctx.deps.task}

    ## Agent Instructions and Tool Calls
    ````````
    {yaml.safe_dump(message_dump)}
    ```````

    ## Evaluation Criteria
    {ctx.deps.criteria}
    """
