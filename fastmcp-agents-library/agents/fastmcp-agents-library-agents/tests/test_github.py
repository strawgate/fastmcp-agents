from typing import TYPE_CHECKING, Any

import pytest
from pydantic_ai.agent import AgentRunResult
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from fastmcp_agents.library.agents.github.agents import github_triage_agent
from fastmcp_agents.library.agents.github.models import GitHubIssue, GitHubIssueSummary
from fastmcp_agents.library.agents.shared.models import Failure

from .conftest import assert_passed, evaluation_rubric, split_dataset

if TYPE_CHECKING:
    from pydantic_evals.reporting import EvaluationReport


def test_init_agents():
    assert github_triage_agent is not None


@pytest.mark.asyncio
async def test_call_agent():
    investigate_issue = GitHubIssue(
        issue_number=1,
        owner="strawgate",
        repo="fastmcp-agents-tests-e2e",
    )

    result: AgentRunResult[GitHubIssueSummary | Failure] = await github_triage_agent.run(
        user_prompt="The issue number to gather background information for is 1.",
        deps=(investigate_issue, None),
    )

    assert result is not None
    assert result.output is not None
    assert isinstance(result.output, GitHubIssueSummary)
    assert result.output.title is not None
    assert result.output.detailed_summary is not None


class CaseInput(GitHubIssue):
    pass


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
            inputs=CaseInput(owner="strawgate", repo="fastmcp-agents-tests-e2e", issue_number=1),
        ),
        Case(
            name="bug: Agent fails to handle empty response from model",
            inputs=CaseInput(owner="strawgate", repo="fastmcp-agents-tests-e2e", issue_number=2),
        ),
        Case(
            name="enhancement: Improve API documentation",
            inputs=CaseInput(owner="strawgate", repo="fastmcp-agents-tests-e2e", issue_number=3),
        ),
    ],
)


dataset_names, datasets = split_dataset(dataset)


@pytest.mark.parametrize("dataset", datasets, ids=dataset_names)
async def test_investigation_cases(dataset: Dataset):
    async def run_gather_background(case_input: CaseInput) -> AgentRunResult[GitHubIssueSummary | Failure]:
        return await github_triage_agent.run(
            user_prompt=f"The issue number to gather background information for is {case_input.issue_number}.",
            deps=(case_input, None),
        )

    evaluation: EvaluationReport[GitHubIssueSummary | Failure, Any, Any] = await dataset.evaluate(
        task=run_gather_background,
        name="GitHub Agent",
    )

    assert_passed(evaluation_report=evaluation)
