import tempfile
from collections.abc import Awaitable, Callable, Generator
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessage
from pydantic_evals import Dataset
from pydantic_evals.evaluators.llm_as_a_judge import set_default_judge_model
from pydantic_evals.reporting import EvaluationReport, ReportCaseAggregate

set_default_judge_model(model="google-gla:gemini-2.5-flash")


def assert_passed(evaluation_report: EvaluationReport, print_report: bool = True) -> None:
    agg_score: ReportCaseAggregate = evaluation_report.averages()
    avg_score = list(agg_score.scores.values())
    if print_report:
        print(f"Evaluation report for {evaluation_report.name}:")
        evaluation_report.print(include_averages=False, include_output=True, width=120)
    assert all(score > 0.9 for score in avg_score)


async def run_evaluation[T](name: str, dataset: Dataset, task: Callable[..., Awaitable[AgentRunResult[T]]]) -> EvaluationReport:
    async def evaluation_wrapper(input_dict: dict[str, Any]) -> tuple[T, list[ModelMessage]]:
        result: AgentRunResult[T] = await task(**input_dict)

        return result.output, result.all_messages()

    evaluation: EvaluationReport[Any, Any, Any] = await dataset.evaluate(task=evaluation_wrapper, name=name)

    # assert_passed(evaluation_report=evaluation)

    return evaluation


async def run_multi_agent_evaluation[T](
    name: str, dataset: Dataset, task: Callable[..., Awaitable[tuple[AgentRunResult[T], ...]]]
) -> EvaluationReport:
    async def evaluation_wrapper(input_dict: dict[str, Any]) -> list[tuple[T, list[ModelMessage]]]:
        results: tuple[AgentRunResult[T], ...] = await task(**input_dict)

        return [(result.output, result.all_messages()) for result in results]

    evaluation: EvaluationReport[Any, Any, Any] = await dataset.evaluate(task=evaluation_wrapper, name=name)

    return evaluation


def evaluation_rubric(criteria: str) -> str:
    base_criteria = """Evaluate the task on both the final result as well as the tool calls and their responses to ensure
    that each item of the final result is based off of information gathered during a "tool call" or from the "user prompt" =
    in the conversation history. The evaluation should fail if there were excessive unnecessary tool calls or if the result
    includes information fabricated after a tool call failed. Every piece of information the Agent provides should be traceable
    back to a tool call response or the user prompt."""
    return base_criteria + f"\n\n{criteria}"


@pytest.fixture(name="temp_dir")
def temporary_directory() -> Generator[Path]:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def split_dataset(dataset: Dataset) -> tuple[list[str], list[Dataset[Any, Any, Any]]]:
    """Splits the cases of a dataset into their own datasets."""

    names: list[str] = []
    datasets: list[Dataset[Any, Any, Any]] = []

    for case in dataset.cases:
        names.append(case.name or "case")
        datasets.append(Dataset(cases=[case], evaluators=dataset.evaluators))

    return names, datasets
