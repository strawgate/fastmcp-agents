import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, ClassVar

import pytest
import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.agent import Agent
from pydantic_ai.output import OutputDataT
from pydantic_ai.run import AgentRunResult
from pydantic_ai.tools import AgentDepsT
from pydantic_evals.dataset import Case, Dataset
from pydantic_evals.evaluators import LLMJudge
from pydantic_evals.evaluators.llm_as_a_judge import set_default_judge_model
from pydantic_evals.reporting import EvaluationReport, ReportCaseAggregate
from rich.pretty import pprint

TESTING_MODEL = "google-gla:gemini-2.5-flash"

set_default_judge_model(model=TESTING_MODEL)


def assert_passed(evaluation_report: EvaluationReport, print_report: bool = True) -> None:
    agg_score: ReportCaseAggregate = evaluation_report.averages()
    avg_score = list(agg_score.scores.values())
    if print_report:
        print(f"Evaluation report for {evaluation_report.name}:")
        for case in evaluation_report.cases:
            print(f"Case: {case.name}")
            print("===Inputs===")
            print(pprint(case.inputs))
            print("===Output===")
            output = case.output
            if isinstance(output, AgentRunResult):
                run_result_output: Any = output.output  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                if isinstance(run_result_output, BaseModel):
                    print(yaml.safe_dump(run_result_output.model_dump()))
                else:
                    pprint(run_result_output)
            else:
                pprint(output)

            print("===Assertions===")
            for assertion_name, assertion_result in case.assertions.items():
                print(f"{assertion_name}: {assertion_result.reason}")

        evaluation_report.print(include_averages=False, width=120)
    assert all(score > 0.9 for score in avg_score)


class AgentRunInput[AgentDepsT](BaseModel):
    """An input for an agent run."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    deps: AgentDepsT

    user_prompt: str | None = None
    kwargs: dict[str, Any] = Field(default_factory=dict)

    async def run(self, agent: Agent[AgentDepsT, OutputDataT]) -> AgentRunResult[OutputDataT]:
        """Run the agent."""
        agent_run_result: AgentRunResult[OutputDataT] = await agent.run(
            model=TESTING_MODEL,
            user_prompt=self.user_prompt,
            deps=self.deps,
            **self.kwargs,
        )

        return agent_run_result

    def to_case(self, name: str) -> Case["AgentRunInput[AgentDepsT]", Any, Any]:
        """Convert the input to a case."""
        return Case[AgentRunInput[AgentDepsT], Any, Any](
            name=name,
            inputs=self,
        )


async def evaluate_agent_cases(
    agent: Agent[AgentDepsT, OutputDataT],
    cases: list[Case[AgentRunInput[AgentDepsT], Any, Any]],
    criteria: str | None = None,
) -> list[EvaluationReport[Any, Any, Any]]:
    """Run an evaluation for a given task."""

    judge: tuple[LLMJudge] = (
        LLMJudge(
            score={"evaluation_name": "investigation", "include_reason": True},
            include_input=True,
            rubric=evaluation_rubric(
                criteria=criteria,
            ),
        ),
    )

    evaluations: list[EvaluationReport[Any, Any, Any]] = []

    for case in cases:
        case.inputs = case.inputs or {}

        dataset: Dataset[AgentRunInput[AgentDepsT], Any, Any] = Dataset(
            evaluators=judge,
            cases=cases,
        )

        async with agent:

            async def run_agent(case_input: AgentRunInput[AgentDepsT]) -> AgentRunResult[OutputDataT]:
                return await case_input.run(agent=agent)

            evaluation: EvaluationReport[AgentRunInput[AgentDepsT], Any, Any] = await dataset.evaluate(
                max_concurrency=1,
                task=run_agent,
                name="Evaluate Agent Task",
            )

        assert_passed(evaluation_report=evaluation)

        evaluations.append(evaluation)

    return evaluations


async def evaluate_agent_case(
    agent: Agent[AgentDepsT, OutputDataT],
    case: Case[AgentRunInput[AgentDepsT], Any, Any],
    criteria: str | None = None,
) -> EvaluationReport[Any, Any, Any]:
    """Run an evaluation for a given task."""

    return (
        await evaluate_agent_cases(
            agent=agent,
            cases=[case],
            criteria=criteria,
        )
    )[0]


def evaluation_rubric(criteria: str | None = None) -> str:
    base_criteria = """Evaluate the task on both the final result as well as the tool calls and their responses to ensure
    that each item of the final result is based off of information gathered during a "tool call" or from the "user prompt" =
    in the conversation history. The evaluation should fail if there were excessive unnecessary tool calls or if the result
    includes information fabricated after a tool call failed. Every piece of information the Agent provides should be traceable
    back to a tool call response or the user prompt."""

    return base_criteria + f"\n\n{criteria}"


@pytest.fixture(name="temp_dir")
async def temporary_directory() -> AsyncGenerator[Path, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


# def split_dataset(dataset: Dataset) -> tuple[list[str], list[Dataset[Any, Any, Any]]]:
#     """Splits the cases of a dataset into their own datasets."""

#     names: list[str] = []
#     datasets: list[Dataset[Any, Any, Any]] = []

#     for case in dataset.cases:
#         names.append(case.name or "case")
#         datasets.append(Dataset(cases=[case], evaluators=dataset.evaluators))

#     return names, datasets


# class TestCase(BaseModel):
#     user_prompt: str
#     deps: Any
#     rubric: str


@pytest.fixture(autouse=True)
async def auto_instrument_agents():
    from fastmcp_agents.library.agents.shared.logging import configure_console_logging

    configure_console_logging()
