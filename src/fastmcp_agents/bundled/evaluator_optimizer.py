"""Tools for evaluating and optimizing task results."""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, Literal

import asyncclick as click
import yaml
from fastmcp import Context, FastMCP
from fastmcp.tools import FunctionTool
from pydantic import BaseModel, Field, computed_field

from fastmcp_agents.agent.fastmcp import FastMCPAgent
from fastmcp_agents.conversation.types import Conversation

evaluator = FastMCPAgent(
    name="task_result_evaluator",
    description="Evaluates the result of a task and provides feedback on the quality of the result.",
    system_prompt="You are a helpful assistant that evaluates the result of a task and provides feedback on the quality of the result.",
)

A: float = 0.9
B: float = 0.8
C: float = 0.7
D: float = 0.6
F: float = 0.0


class CriteriaNotes(BaseModel):
    """A judging criteria with notes."""

    criteria: str = Field(..., description="The description of the criteria.")
    notes: str = Field(..., description="Any notes on the criteria.")


class CriteriaScore(CriteriaNotes):
    """A judging criteria with a score and notes."""

    max_points: int = Field(..., description="The maximum points of the score part.", ge=0)
    points: int = Field(..., description="The points of the score part.", ge=0)


class EvaluationResult(BaseModel):
    """A result of an evaluation."""

    criteria: list[CriteriaScore] = Field(..., description="The criteria for the evaluation.")

    @property
    def feedback(self) -> dict[str, str]:
        """Get the feedback for the evaluation."""
        return {criteria.criteria: criteria.notes for criteria in self.criteria if criteria.notes}

    @computed_field(return_type=float)
    def grade(self):
        """Get the grade for the evaluation."""
        return self._grade()

    @computed_field
    def letter_grade(self) -> Literal["A", "B", "C", "D", "F"]:
        """Get the letter grade for the evaluation."""
        grade: float = self._grade()
        if grade >= A:
            return "A"
        if grade >= B:
            return "B"
        if grade >= C:
            return "C"
        if grade >= D:
            return "D"
        return "F"

    def _grade(self):
        """Get the grade for the evaluation."""
        # Pylance was being weird so I moved it into a private function
        if not self.criteria:
            return 0.0
        return sum(criteria.points for criteria in self.criteria) / sum(criteria.max_points for criteria in self.criteria)


class EvaluationError(Exception):
    """An error that occurs during evaluation."""

    def __init__(self, message: str):
        """Initialize the error."""
        super().__init__(message)


def build_prompt(goal: str, proposed_solution: str, criteria: str, conversation_history: Conversation | None = None) -> str:
    """Build the prompt for the evaluation."""
    prompt = EVALUATION_PREAMBLE

    format_kwargs = {
        "goal": goal,
        "proposed_solution": proposed_solution,
        "criteria": criteria,
    }

    if conversation_history:
        prompt += CONVERSATION_SUFFIX
        format_kwargs["conversation_history"] = yaml.safe_dump(
            compress_messages(conversation_history.to_messages()), indent=2, sort_keys=True
        )

    return prompt.format(**format_kwargs)


def compress_message(message: dict[str, Any]) -> dict[str, Any]:
    """Compress a message to 1KB."""
    for key, value in message.items():
        if isinstance(value, str) and len(value) > ONE_KB:
            message[key] = value[:ONE_KB] + "..."
    return message


def compress_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compress a list of messages to 1KB."""
    return [compress_message(message) for message in messages]


ONE_KB = 1024


async def perform_evaluation(ctx: Context, prompt: str) -> EvaluationResult:
    _, evaluation_result = await evaluator.run(
        ctx,
        task=prompt,
        success_response_model=EvaluationResult,
        raise_on_error_response=True,
    )

    if not isinstance(evaluation_result, EvaluationResult):
        raise EvaluationError(message="The evaluation result is not a EvaluationResult")

    return evaluation_result


async def evaluate_conversation(
    ctx: Context, criteria: str, goal: str, proposed_solution: str, conversation: Conversation
) -> EvaluationResult:
    prompt = build_prompt(
        goal=goal,
        proposed_solution=proposed_solution,
        criteria=criteria,
        conversation_history=conversation,
    )

    return await perform_evaluation(ctx, prompt)


async def evaluate_result(ctx: Context, criteria: str, goal: str, proposed_solution: str) -> EvaluationResult:
    """Evaluate the result of a task."""
    prompt = build_prompt(goal=goal, proposed_solution=proposed_solution, criteria=criteria)

    return await perform_evaluation(ctx, prompt)


def evaluate_conversation_factory(criteria: str) -> Callable[..., Coroutine[Any, Any, EvaluationResult]]:
    """A factory for creating evaluation functions with a fixed criteria."""

    async def evaluate(ctx: Context, goal: str, proposed_solution: str, conversation: Conversation) -> EvaluationResult:
        return await evaluate_conversation(
            ctx=ctx, criteria=criteria, goal=goal, proposed_solution=proposed_solution, conversation=conversation
        )

    return evaluate


def evaluate_result_factory(criteria: str) -> Callable[..., Coroutine[Any, Any, EvaluationResult]]:
    """A factory for creating evaluation functions with a fixed criteria."""

    async def evaluate(ctx: Context, goal: str, proposed_solution: str) -> EvaluationResult:
        return await evaluate_result(ctx=ctx, criteria=criteria, goal=goal, proposed_solution=proposed_solution)

    return evaluate


@click.command()
@click.option(
    "--evaluation-criteria",
    type=str,
    envvar="evaluation_criteria",
    help="The evaluation criteria to use for scoring the result.",
)
async def cli(evaluation_criteria: str | None = None):
    evaluator_tool = FunctionTool.from_function(fn=evaluate_result_factory(evaluation_criteria or DEFAULT_CRITERIA))

    mcp = FastMCP(name="Local Evaluate Optimize", tools=[evaluator_tool])

    await mcp.run_async()


def run_mcp():
    asyncio.run(cli())


if __name__ == "__main__":
    run_mcp()

DEFAULT_CRITERIA = """
| Criteria | Description | Points |
|----------|-------------|---------|
| Completeness | The proposed solution is complete, relevant, and covers all the aspects of the goal. | 10 |
| Accuracy | The proposed solution is accurate and correct. | 10 |
| Simplicity | The proposed solution is the simplest answer that totally achieves the stated goal. | 10 |
| Clarity | The proposed solution is clear and easy to understand. | 10 |
"""

EVALUATION_PREAMBLE = """
You are a helpful assistant that evaluates the final work product of someone who has been working to achieve a goal.

You will not do any of the work yourself, you are only evaluating the final work product. You are an objective observer
who is not swayed by errors encountered, problems, etc. You only care whether the work product achieves the goal.

You must provide a score between 0 and 100 for the result. You must provide a feedback on the result.

## Illustrative Example

Imagine you are judging a competition.

The task is to: `Write a Python function that calculates the square of a number.`

| Criteria | Description | Points |
|----------|-------------|---------|
| Completeness | The proposed solution is complete, relevant, and covers all the aspects of the goal. | 10 |
| Accuracy | The proposed solution is accurate and correct. | 10 |
| Simplicity | The proposed solution is the simplest answer that totally achieves the stated goal. | 10 |
| Clarity | The proposed solution is clear and easy to understand. | 10 |


The proposed solution is:
```python
def multiply(x, y):
    if not isinstance(x, int) or not isinstance(y, int):
        raise ValueError("x and y must be integers")
    return x * y

def square(x):
    first_x = x
    second_x = x
    return multiply(first_x, second_x)
```

You thoroughly evaluate the proposed solution and provide a score and feedback on the result.

| Criteria | Score | Notes |
|----------|-------|-------|
| Completeness | 10 | None |
| Accuracy | 10 | None |
| Simplicity | 4 | A simpler solution would be to use the `**` operator. |
| Clarity | 9 | The code would be more clear if it was commented. |

Total Score: 33 out of 40 (82.5%)

# The Evaluation

The goal of the task is:
```
{goal}
```

The proposed solution is:
```
{proposed_solution}
```

The evaluation criteria is:
```markdown
{criteria}
```
"""

CONVERSATION_SUFFIX = """
The conversation history is:
```
{conversation_history}
```

Note: This is a worklog from the agent that was working to achieve the goal. Entries longer than 1000 characters have
been truncated and will end with "..." to indicate that they have been truncated.

You can check the worklog to make sure that the agent:
1) did not miss any important information
2) did not make any mistakes
3) did not invent a positive result that was not actually achieved
"""
