import asyncio
from typing import Any, Callable, Coroutine, Literal

import asyncclick as click
from fastmcp import Context, FastMCP
from fastmcp.tools import Tool as FastMCPTool
from pydantic import BaseModel, Field, computed_field

from fastmcp_agents.agent.basic import FastMCPAgent
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
    criteria: str = Field(..., description="The description of the criteria.")
    notes: str = Field(..., description="Any notes on the criteria.")


class CriteriaScore(CriteriaNotes):
    max_points: int = Field(..., description="The maximum points of the score part.", ge=0)
    points: int = Field(..., description="The points of the score part.", ge=0)


class EvaluationResult(BaseModel):
    criteria: list[CriteriaScore] = Field(..., description="The criteria for the evaluation.")

    @property
    def feedback(self) -> dict[str, str]:
        return {criteria.criteria: criteria.notes for criteria in self.criteria if criteria.notes}

    @computed_field(return_type=float)
    def grade(self):
        return self._grade()

    @computed_field
    def letter_grade(self) -> Literal["A", "B", "C", "D", "F"]:
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
        # Pylance was being weird so I moved it into a private function
        if not self.criteria:
            return 0.0
        return sum(criteria.points for criteria in self.criteria) / sum(criteria.max_points for criteria in self.criteria)


class EvaluationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


DEFAULT_EVALUATION_CRITERIA = """
You are a helpful assistant that evaluates the final work product of someone who has been working to achieve a goal.

You will not do any of the work yourself, you are only evaluating the final work product. You are an objective observer
who is not swayed by errors encountered, problems, etc. You only care whether the work product achieves the goal.

Here is your grading rubric

| Criteria | Description | Points |
|----------|-------------|---------|
| Completeness | The proposed solution is complete, relevant, and covers all the aspects of the goal. | 10 |
| Accuracy | The proposed solution is accurate and correct. | 10 |
| Simplicity | The proposed solution is the simplest answer that totally achieves the stated goal. | 10 |
| Clarity | The proposed solution is clear and easy to understand. | 10 |

Example:

Goal: "Write a Python function that calculates the square of a number."

Proposed Solution:
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

| Criteria | Score | Notes |
|----------|-------|-------|
| Completeness | 10 | None |
| Accuracy | 10 | None |
| Simplicity | 4 | A simpler solution would be to use the `**` operator. |
| Clarity | 9 | The code would be more clear if it was commented. |

Total Score: 33 out of 40 (82.5%)
"""


def evaluate_conversation_factory(criteria: str) -> Callable[..., Coroutine[Any, Any, EvaluationResult]]:
    async def evaluate_conversation(ctx: Context, goal: str, proposed_solution: str, conversation: Conversation) -> EvaluationResult:
        formatted_conversation_history: str = ""

        for message in conversation.to_messages():
            content = message.get("content", "")
            if len(content) > 1000:
                content = content[:1000] + "..."

        _, evaluation_result = await evaluator.run(
            ctx,
            instructions=f"""
        You are a helpful assistant that evaluates the result of a task done by someone else and provides
        feedback on the quality of the result. You will not do any of the work yourself, you are only evaluating
        the result.

        The goal of the task was: `{goal}`
        The proposed solution is:
        ```
        {proposed_solution}
        ```

        The evaluation criteria is:
        ```markdown
        {criteria}
        ```

        The conversation history is:
        ```
        {formatted_conversation_history}
        ```

        Note: This is a worklog from the agent that was working to achieve the goal. Entries longer than 1000 characters have
        been truncated and will end with "..." to indicate that they have been truncated. You can check the worklog
        to make sure that the agent 1) did not miss any important information and 2) did not make any mistakes, 3) did not invent
        a positive result that was not actually achieved.

        You must provide a score between 0 and 100 for the result.

        You must provide a feedback on the result.

        You must provide a list of recommendations for improving the result. The list of recommendations should focus
        on what guidance could be provided to the person who did the work to improve the result.
        """,
            success_response_model=EvaluationResult,
            raise_on_error_response=True,
        )

        if not isinstance(evaluation_result, EvaluationResult):
            raise EvaluationError(message="The evaluation result is not a EvaluationResult")

        return evaluation_result

    return evaluate_conversation


def evaluate_result_factory(criteria: str) -> Callable[..., Coroutine[Any, Any, EvaluationResult]]:

    async def evaluate_result(ctx: Context, goal: str, proposed_solution: str) -> EvaluationResult:
        _, evaluation_result = await evaluator.run(
            ctx,
            instructions=f"""
        You are a helpful assistant that evaluates the result of a task done by someone else and provides
        feedback on the quality of the result. You will not do any of the work yourself, you are only evaluating
        the result.

        The goal of the task is: `{goal}`
        The proposed solution is: `{proposed_solution}`

        The evaluation criteria is:
        ```markdown
        {criteria}
        ```

        You must provide a score between 0 and 100 for the result.

        You must provide a feedback on the result.

        You must provide a list of recommendations for improving the result. The list of recommendations should focus
        on what guidance could be provided to the person who did the work to improve the result.
        """,
            success_response_model=EvaluationResult,
            raise_on_error_response=True,
        )

        if not isinstance(evaluation_result, EvaluationResult):
            raise EvaluationError(message="The evaluation result is not a EvaluationResult")

        return evaluation_result

    return evaluate_result


@click.command()
@click.option(
    "--evaluation-criteria",
    type=str,
    envvar="evaluation_criteria",
    help="The evaluation criteria to use for scoring the result.",
)
async def cli(evaluation_criteria: str | None = None):
    evaluator_tool = FastMCPTool.from_function(fn=evaluate_result_factory(evaluation_criteria or DEFAULT_EVALUATION_CRITERIA))

    mcp = FastMCP(name="Local Evaluate Optimize", tools=[evaluator_tool])

    await mcp.run_async()


def run_mcp():
    asyncio.run(cli())


if __name__ == "__main__":
    run_mcp()
