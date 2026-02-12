from typing import TYPE_CHECKING, Any

import pytest
from pydantic import BaseModel
from pydantic_ai.agent import AgentRunResult
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from fastmcp_agents.library.agents.github.agents.research_agent import ResearchAgentInput, github_research_agent
from fastmcp_agents.library.agents.github.dependencies.github import GitHubRelatedItems

from .conftest import assert_passed, evaluation_rubric, split_dataset

if TYPE_CHECKING:
    from pydantic_evals.reporting import EvaluationReport


def test_init_agents():
    assert github_research_agent is not None


@pytest.mark.asyncio
async def test_call_agent():
    research_agent_input = ResearchAgentInput(
        issue_owner="strawgate",
        issue_repo="fastmcp-agents",
        issue_number=1,
    )

    result: AgentRunResult[GitHubRelatedItems] = await github_research_agent.run(
        user_prompt="Please gather background information for the issue.",
        deps=research_agent_input.to_deps(),
    )

    assert result is not None
    assert result.output is not None


class CaseInput(BaseModel):
    owner: str
    repo: str
    issue_number: int


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
    async def run_gather_background(case_input: CaseInput) -> AgentRunResult[GitHubRelatedItems]:
        research_agent_input = ResearchAgentInput(
            issue_owner=case_input.owner,
            issue_repo=case_input.repo,
            issue_number=case_input.issue_number,
        )

        agent_result = await github_research_agent.run(
            user_prompt=f"The issue number to gather background information for is {case_input.issue_number}.",
            deps=research_agent_input.to_deps(),
        )

        return agent_result

    evaluation: EvaluationReport[GitHubRelatedItems, Any, Any] = await dataset.evaluate(
        task=run_gather_background,
        name="GitHub Agent",
    )

    assert_passed(evaluation_report=evaluation)
