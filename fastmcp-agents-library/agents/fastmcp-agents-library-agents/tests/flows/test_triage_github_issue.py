import os
from collections.abc import Generator
from typing import Any

import pytest
from fastmcp_agents.library.agents.flows.triage_github_issue import private_fork_triage_github_issue_raw, triage_github_issue_raw
from github import Github
from github.Auth import Token
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from ..conftest import assert_passed, evaluation_rubric, run_multi_agent_evaluation, split_dataset


def test_init_agents():
    assert private_fork_triage_github_issue_raw is not None
    assert triage_github_issue_raw is not None


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


def get_github_client() -> Github:
    token: str | None = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    if token is None:
        msg = "No GitHub token found"
        raise ValueError(msg)

    return Github(auth=Token(token=token))


def delete_comments(dataset: Dataset):
    github_client = get_github_client()
    for case in dataset.cases:
        issue = github_client.get_repo(f"{case.inputs['owner']}/{case.inputs['repo']}").get_issue(int(case.inputs["issue_number"]))

        for comment in issue.get_comments():
            comment.delete()


@pytest.fixture(autouse=True)
def clean_up_issues() -> Generator[None, Any]:
    delete_comments(dataset=dataset)

    yield

    delete_comments(dataset=dataset)


dataset_names, datasets = split_dataset(dataset)


@pytest.mark.parametrize("dataset", datasets, ids=dataset_names)
async def test_triage_github_issue_cases(dataset: Dataset):
    evaluation = await run_multi_agent_evaluation(name="triage_github_issue", dataset=dataset, task=triage_github_issue_raw)

    assert_passed(evaluation_report=evaluation)
