import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from fastmcp_agents.library.agents.filesystem.agents import read_only_filesystem_agent, read_write_filesystem_agent

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult


def test_init_agents():
    assert read_only_filesystem_agent is not None
    assert read_write_filesystem_agent is not None


@pytest.fixture
async def temporary_filesystem() -> AsyncGenerator[Path, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        subdir = Path(temp_dir) / "subdir"
        subdir.mkdir()
        file_one = subdir / "file_one.txt"
        file_one.write_text("Hello, world!")
        file_two = subdir / "file_two.txt"
        file_two.write_text("Hello, world!")
        subdir_two = subdir / "subdir_two"
        subdir_two.mkdir()
        file_three = subdir_two / "file_three.txt"
        file_three.write_text("Goodbye, world!")

        yield Path(temp_dir).resolve()


@pytest.mark.asyncio
async def test_call_agent(temporary_filesystem: Path):
    result: AgentRunResult[int] = await read_only_filesystem_agent.run(
        user_prompt="How many files say Hello in them?",
        deps=temporary_filesystem,
        output_type=int,
    )

    assert result is not None
    assert result.output is not None
    assert result.output == 2


# dataset = Dataset(
#     evaluators=[
#         LLMJudge(
#             score={"evaluation_name": "investigation", "include_reason": True},
#             include_input=True,
#             rubric=evaluation_rubric(
#                 criteria="""The agent's message history confirms it looked up the issue,
#                 searched for related issues, and did not fabricate any information."""
#             ),
#         ),
#     ],
#     cases=[
#         Case(
#             name="enhancement: Add support for custom model configurations",
#             inputs=CaseInput(owner="strawgate", repo="fastmcp-agents-tests-e2e", issue_number=1),
#         ),
#         Case(
#             name="bug: Agent fails to handle empty response from model",
#             inputs=CaseInput(owner="strawgate", repo="fastmcp-agents-tests-e2e", issue_number=2),
#         ),
#         Case(
#             name="enhancement: Improve API documentation",
#             inputs=CaseInput(owner="strawgate", repo="fastmcp-agents-tests-e2e", issue_number=3),
#         ),
#     ],
# )


# dataset_names, datasets = split_dataset(dataset)


# @pytest.mark.parametrize("dataset", datasets, ids=dataset_names)
# async def test_investigation_cases(dataset: Dataset):
#     async def run_gather_background(case_input: CaseInput) -> AgentRunResult[GitHubIssueSummary | Failure]:
#         return await github_triage_agent.run(
#             user_prompt=f"The issue number to gather background information for is {case_input.issue_number}.",
#             deps=(case_input, None),
#         )

#     evaluation: EvaluationReport[GitHubIssueSummary | Failure, Any, Any] = await dataset.evaluate(
#         task=run_gather_background,
#         name="GitHub Agent",
#     )

#     assert_passed(evaluation_report=evaluation)
