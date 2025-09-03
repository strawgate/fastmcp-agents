import os
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import git
import pytest
from git import Repo
from github.ContentFile import ContentFile
from github.Issue import Issue
from github.MainClass import Github
from github.PullRequest import PullRequest
from github.Repository import Repository

if TYPE_CHECKING:
    from github.GitRef import GitRef


@pytest.fixture
def github_client() -> Github:
    """Create a GitHub client using the GITHUB_TOKEN environment variable."""
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN environment variable not set")
    return Github(login_or_token=token)


@pytest.fixture
def test_repo(github_client: Github) -> Repository:
    """Get the test repository."""
    return github_client.get_repo("strawgate/fastmcp-agents-tests-e2e")


@pytest.fixture
async def clone_repo(test_repo: Repository) -> AsyncGenerator[Path, Any]:
    """Clone the test repository."""
    with tempfile.TemporaryDirectory() as temp_dir:
        git.Repo.clone_from(test_repo.clone_url, temp_dir)
        yield Path(temp_dir)


@pytest.fixture(autouse=True)
def close_test_issues(test_repo: Repository):
    """Close all test issues."""
    existing_issues = test_repo.get_issues(state="open")

    for issue in existing_issues:
        issue.edit(state="closed", title="Removed", body="Removed")


@pytest.fixture(autouse=True)
def close_test_prs(test_repo: Repository):
    """Close all test pull requests."""
    existing_prs = test_repo.get_pulls(state="open")
    for pr in existing_prs:
        if pr.title.startswith("Removed"):
            continue
        pr.edit(state="closed", title="Removed", body="Removed")


def create_test_issue(repo: Repository, title: str, body: str, labels: list[str] | None = None) -> Issue:
    """Helper function to create a test issue."""
    return repo.create_issue(title=title, body=body, labels=labels or [])


def force_create_github_branch(repository: Repository, branch: str) -> None:
    """Force create a branch in the repository. If the branch already exists, delete it."""
    try:
        ref: GitRef = repository.get_git_ref(ref=f"heads/{branch}")
        ref.delete()
    except Exception:  # noqa: S110
        pass

    repository.create_git_ref(ref=f"refs/heads/{branch}", sha=repository.get_branch("main").commit.sha)


def get_file_contents(repository: Repository, path: str, ref: str | None = None) -> ContentFile:
    """Get the contents of a file in the repository."""

    file_or_files: list[ContentFile] | ContentFile = repository.get_contents(path, ref=ref) if ref else repository.get_contents(path)

    if isinstance(file_or_files, list):
        return file_or_files[0]

    return file_or_files


def get_file_contents_str(repository: Repository, path: str, ref: str | None = None) -> str:
    """Get the contents of a file in the repository as a string."""
    return get_file_contents(repository=repository, path=path, ref=ref).decoded_content.decode("utf-8")


def update_file(repository: Repository, ref: str, path: str, content: str, message: str) -> None:
    """Update the contents of a file in the repository."""
    repository.update_file(
        path=path,
        content=content,
        sha=get_file_contents(repository=repository, path=path, ref=ref).sha,
        message=message,
        branch=ref,
    )


def checkout_pr_branch(repo: Repo | Path, pr: PullRequest) -> None:
    """Checkout the branch of a pull request."""
    if isinstance(repo, Path):
        repo = Repo(repo)
    repo.git.checkout(pr.head.ref)

    # base_criteria = """The Agent's message history confirms that it did not fabricate it's response.
    # All information should be strongly rooted in either:
    # 1. Obvious Knowledge
    # 2. Provided Information
    # 3. Tool calls and responses

    # Any response that is not based on the provided information or from Tool calls is considered fabrication.

    # If the Agent performed invalid, failed, or excessive tool calls, it did not pass the criteria."""

    # if criteria:
    #     criteria = f"{base_criteria}\n\n{criteria}"

    # base_user_prompt = """
    # Please handle the provided user reported GitHub issue.
    # Please note, when searching for issues and pull requests, only search for open ones.
    # If you handoff to other Agents, you must insist that all searches performed are ONLY for open issues and pull requests.
    # """

    # user_prompt = f"{user_prompt!s}\n\n{base_user_prompt}"

    # judge = (
    #     LLMJudge(
    #         score={"evaluation_name": "investigation", "include_reason": True},
    #         include_input=True,
    #         rubric=evaluation_rubric(
    #             criteria=criteria or base_criteria,
    #         ),
    #     ),
    # )

    # dataset = Dataset(
    #     evaluators=judge,
    #     cases=[case],
    # )

    # async def run_implementation(case_input: CaseInput) -> AgentRunResult[AgentResult]:
    #     investigate_issue = IssueDrivenAgentInput(
    #         issue_owner=case_input.owner,
    #         issue_repo=case_input.repo,
    #         issue_number=case_input.issue_number,
    #         agent_settings=IssueTriageAgentSettings(
    #             code_base=clone_repo,
    #         ),
    #     )
    #     return await issue_driven_agent.run(
    #         user_prompt=user_prompt,
    #         deps=investigate_issue.to_deps(),
    #     )

    # evaluation: EvaluationReport[CaseInput, Any, Any] = await dataset.evaluate(
    #     task=run_implementation,
    #     name="GitHub Agent Implementation",
    # )

    # return evaluation
