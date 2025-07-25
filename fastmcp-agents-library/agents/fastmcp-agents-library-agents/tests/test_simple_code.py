from pathlib import Path

import pytest
from fastmcp_agents.library.agents.simple_code.agents import (
    code_implementation_agent,
    code_investigation_agent,
    investigate_code_repository_raw,
)
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from .conftest import assert_passed, evaluation_rubric, run_evaluation, split_dataset


def test_init_agents():
    assert code_investigation_agent is not None
    assert code_implementation_agent is not None


# def assert_passed(evaluation_report: EvaluationReport, print_report: bool = True) -> None:
#     agg_score: ReportCaseAggregate = evaluation_report.averages()
#     avg_score = list(agg_score.scores.values())
#     if print_report:
#         evaluation_report.print()
#     assert all(score > 0.9 for score in avg_score)


calculator_code_base = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    return a / b

def power(a, b):
    return a ** b
"""

dataset = Dataset(
    evaluators=[
        LLMJudge(
            score={"evaluation_name": "investigation", "include_reason": True},
            include_input=True,
            rubric=evaluation_rubric(criteria="The completed investigation matches the task posed to the agent."),
        ),
    ],
    cases=[
        Case(
            name="docs",
            inputs={"task": "Please add a docstring to each function in the calculator.", "code_base": calculator_code_base},
        ),
        Case(
            name="refactor",
            inputs={"task": "Please refactor the calculator to be a class.", "code_base": calculator_code_base},
        ),
    ],
)


dataset_names, datasets = split_dataset(dataset)


@pytest.mark.parametrize("dataset", datasets, ids=dataset_names)
async def test_investigation_cases(dataset: Dataset, temp_dir: Path):
    code_path: Path = temp_dir / "sample_code.py"

    for case in dataset.cases:
        code_path.write_text(case.inputs.pop("code_base"))
        case.inputs["code_repository"] = temp_dir

    evaluation = await run_evaluation(name="investigation", dataset=dataset, task=investigate_code_repository_raw)

    assert_passed(evaluation_report=evaluation)


# cases: list[Case] = [
#     Case(
#         name="docs",
#         inputs={"task": "Please add a docstring to each function in the calculator.", "code_base": code_base},
#         # evaluators=(
#         #     LLMJudge(
#         #         score={"evaluation_name": "investigation_score", "include_reason": True},
#         #         rubric=evaluation_rubric(criteria="The investigation should be able to find the docstrings in the code."),
#         #     ),
#         # ),
#     ),
#     Case(
#         name="refactor",
#         inputs={"task": "Please refactor the calculator to be a class.", "code_base": code_base},
#         # evaluators=(
#         #     LLMJudge(
#         #         score={"evaluation_name": "refactor_score", "include_reason": True},
#         #         rubric=evaluation_rubric(criteria="Verify the calculator has been refactored but is not a class."),
#         #     ),
#         # ),
#     ),
# ]


# @pytest.mark.parametrize("case", cases, ids=[case.name for case in cases])
# async def test_investigation_cases(case: Case, temp_dir: Path):
#     code_path: Path = temp_dir / "sample_code.py"

#     dataset = Dataset(cases=[case])

#     async def investigate_code_repository_wrapper(input_dict: dict[str, Any]) -> tuple[InvestigationResult, list[ModelMessage]]:
#         code_path.write_text(input_dict["code_base"])

#         result: AgentRunResult[InvestigationResult] = await investigate_code_repository_raw(
#             code_repository=temp_dir,
#             task=input_dict["task"],
#         )

#         return result.output, result.all_messages()

#     report = await dataset.evaluate(task=investigate_code_repository_wrapper)  # pyright: ignore[reportArgumentType]

#     assert_passed(evaluation_report=report)


# @pytest.mark.asyncio
# async def test_calculator_investigation(temp_dir: Path):
#     code_path: Path = temp_dir / "sample_code.py"

#     code_path.write_text("""
#     def add(a, b):
#         return a + b

#     def subtract(a, b):
#         return a - b

#     def multiply(a, b):
#         return a * b

#     def divide(a, b):
#         return a / b

#     def power(a, b):
#         return a ** b
#     """)

#     investigation_reponse: InvestigationResponse = await investigate_code_repository(
#         code_repository=temp_dir,
#         task="Please add a docstring to each function in the calculator.",
#     )

#     assert investigation_reponse.branch_info is not None

#     assert isinstance(investigation_reponse, InvestigationResponse)

#     assert investigation_reponse is not None

#     assert len(investigation_reponse.findings) > 0

#     assert investigation_reponse.summary is not None


# @pytest.mark.asyncio
# async def test_calculator_implementation(playground_directory: Path):
#     implementation_response: ImplementationResponse = await implement_code(
#         code_repository=AnyHttpUrl("https://github.com/strawgate/fastmcp-agents-tests-e2e.git"),
#         task="Implement matrix multiplication in the calculator.",
#     )

#     assert isinstance(implementation_response, ImplementationResponse)

#     assert implementation_response.confidence is not None

#     assert implementation_response.summary is not None

#     assert implementation_response.potential_flaws is not None


# @pytest.mark.asyncio
# async def test_many_append_insert_replace(playground_directory: Path):
#     implementation_response: ImplementationResponse = await implement_code(
#         code_repository=AnyHttpUrl("https://github.com/strawgate/fastmcp-agents-tests-e2e.git"),
#         task="""Perform two appends, inserts, and replaces of lines in a file and verify the results. Upon completion, report failure
#         if any of these operations did not work on the first try. If possible please try to explain why you think it did not work""",
#     )

#     assert isinstance(implementation_response, ImplementationResponse)

#     assert implementation_response is not None

#     assert implementation_response.summary is not None

#     assert implementation_response.confidence is not None

#     assert implementation_response.potential_flaws is not None
