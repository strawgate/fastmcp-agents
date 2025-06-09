from typing import Literal

from fastmcp import Context
from pydantic import BaseModel, Field, computed_field

from fastmcp_agents.agent.multi_step import MULTI_STEP_SYSTEM_PROMPT, DefaultErrorResponseModel, MultiStepAgent
from fastmcp_agents.conversation.types import Conversation, SystemConversationEntry, UserConversationEntry

A = 0.9
B = 0.8
C = 0.7
D = 0.6
F = 0.0


SYSTEM_PROMPT = (
    MULTI_STEP_SYSTEM_PROMPT
    + """
You evaluate the final work product of someone who has been working to achieve a goal.

You will not do any of the work yourself, you are only evaluating the final work product. You are an objective observer
who is not swayed by errors encountered, problems, etc. You only care whether the work product achieves the goal.

You must provide a score between 0 and 100 for the result. You must provide a feedback on the result.
"""
)

DEFAULT_INSTRUCTIONS = """
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
"""

DEFAULT_CRITERIA = """
| Criteria | Description | Points |
|----------|-------------|---------|
| Completeness | The proposed solution is complete, relevant, and covers all the aspects of the goal. | 10 |
| Accuracy | The proposed solution is accurate and correct. | 10 |
| Simplicity | The proposed solution is the simplest answer that totally achieves the stated goal. | 10 |
| Clarity | The proposed solution is clear and easy to understand. | 10 |
"""

TASK_TEMPLATE = """
# The Evaluation

The goal of the task was:
```
{goal}
```

The proposed solution is:

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


class EvaluatorAgent(MultiStepAgent):
    """An Agent that uses the tools available on the server to complete a requested task."""

    system_prompt: SystemConversationEntry | str = Field(default=SYSTEM_PROMPT)
    """The system prompt to use."""

    instructions: list[UserConversationEntry] | UserConversationEntry | str = Field(default=DEFAULT_INSTRUCTIONS)

    criteria: str = Field(default=DEFAULT_CRITERIA)

    async def evaluate_result(
        self,
        ctx: Context,
        task: str,
        proposed_solution: str,
        conversation: Conversation,
    ) -> EvaluationResult | DefaultErrorResponseModel:
        """Evaluates a result using the Agent's default instructions.

        Args:
            task: The task to evaluate.
            proposed_solution: The proposed solution to evaluate.
            conversation: The conversation history to evaluate.
        """

        task = TASK_TEMPLATE.format(
            goal=task, proposed_solution=proposed_solution, criteria=self.criteria, conversation_history=conversation
        )

        _, evaluation_result = await self.run_steps(ctx=ctx, task=task, success_response_model=EvaluationResult)

        return evaluation_result
