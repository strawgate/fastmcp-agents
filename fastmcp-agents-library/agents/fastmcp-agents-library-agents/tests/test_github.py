import pytest
from fastmcp_agents.library.agents.github.agents import (
    comment_on_github_issue_raw,
    gather_github_issue_background_raw,
)
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from .conftest import assert_passed, evaluation_rubric, run_evaluation, split_dataset


def test_init_agents():
    assert gather_github_issue_background_raw is not None
    assert comment_on_github_issue_raw is not None


dataset = Dataset(
    evaluators=[
        LLMJudge(
            score={"evaluation_name": "investigation", "include_reason": True},
            include_input=True,
            rubric=evaluation_rubric(
                criteria="""The agent's message history confirms it looked up the issue,
                searched for related issues, and did not fabricate any information."""
            ),
        ),
    ],
    cases=[
        Case(
            name="enhancement: Add support for custom model configurations",
            inputs={"owner": "strawgate", "repo": "fastmcp-agents-tests-e2e", "issue_number": 1},
        ),
        Case(
            name="bug: Agent fails to handle empty response from model",
            inputs={"owner": "strawgate", "repo": "fastmcp-agents-tests-e2e", "issue_number": 2},
        ),
        Case(
            name="enhancement: Improve API documentation",
            inputs={"owner": "strawgate", "repo": "fastmcp-agents-tests-e2e", "issue_number": 3},
        ),
    ],
)


dataset_names, datasets = split_dataset(dataset)


@pytest.mark.parametrize("dataset", datasets, ids=dataset_names)
async def test_gather_background_cases(dataset: Dataset):
    evaluation = await run_evaluation(name="gather_background", dataset=dataset, task=gather_github_issue_background_raw)

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
