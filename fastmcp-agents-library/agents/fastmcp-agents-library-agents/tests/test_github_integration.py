import os
from collections.abc import AsyncGenerator
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any

import pytest
from git import Repo
from gitdb.db.loose import tempfile
from github import Github
from github.ContentFile import ContentFile
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Repository import Repository
from pydantic_ai.agent import AgentRunResult
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from fastmcp_agents.library.agents.github.agents import issue_driven_agent
from fastmcp_agents.library.agents.github.models import GitHubIssue, IssueDrivenAgentInput, IssueDrivenAgentOptions
from fastmcp_agents.library.agents.shared.models import Failure

from .conftest import assert_passed, evaluation_rubric

if TYPE_CHECKING:
    from pydantic_evals.reporting import EvaluationReport


@pytest.fixture
def github_client():
    """Create a GitHub client using the GITHUB_TOKEN environment variable."""
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN environment variable not set")
    return Github(token)


@pytest.fixture
def test_repo(github_client: Github) -> Repository:
    """Get the test repository."""
    return github_client.get_repo("strawgate/fastmcp-agents-tests-e2e")


@pytest.fixture
async def clone_repo(test_repo: Repository) -> AsyncGenerator[Path, Any]:
    """Clone the test repository."""
    with tempfile.TemporaryDirectory() as temp_dir:
        Repo.clone_from(test_repo.clone_url, temp_dir)
        yield Path(temp_dir)


@pytest.fixture
async def test_issues(test_repo: Repository) -> AsyncGenerator[list[Issue], Any]:
    """Create test issues in the repository."""

    existing_issues = test_repo.get_issues(state="open")
    for issue in existing_issues:
        if issue.title.startswith("Removed"):
            continue
        issue.edit(state="closed", title="Removed", body="Removed")

    issues: list[Issue] = []

    # Create a feature request
    feature_request = test_repo.create_issue(
        title="Add support for matrix operations",
        body=dedent("""
        ## Feature Request

        It would be great to add matrix operations to the calculator.

        ### Use Case
        - Allow users to perform matrix addition and multiplication
        - Support matrix transposition
        - Enable matrix determinant calculation

        ### Additional Context
        This would make the calculator more useful for scientific and engineering calculations.
        """),
        labels=["enhancement"],
    )
    issues.append(feature_request)

    # Create a bug report
    bug_report = test_repo.create_issue(
        title="Calculator crashes when dividing by zero",
        body=dedent("""
        ## Bug Report

        The calculator crashes when attempting to divide by zero.

        ### Steps to Reproduce
        1. Create a new calculator instance
        2. Call divide(5, 0)
        3. Calculator crashes with ValueError

        ### Expected Behavior
        Calculator should handle division by zero gracefully with a clear error message

        ### Actual Behavior
        Calculator crashes with ValueError: Division by zero
        """),
        labels=["bug"],
    )
    issues.append(bug_report)

    # Create a related bug report about multiplication by zero
    related_bug = test_repo.create_issue(
        title="Calculator incorrectly returns 0 for multiplication by zero",
        body=dedent("""
        ## Bug Report

        The calculator incorrectly returns 0 when multiplying by zero.

        ### Steps to Reproduce
        1. Create a new calculator instance
        2. Call multiply(5, 0)
        3. Calculator returns 0

        ### Expected Behavior
        Calculator should return 0 for multiplication by zero, but should handle this case explicitly
        and provide a clear message to the user that the result is 0 because one of the operands is 0.

        ### Actual Behavior
        Calculator silently returns 0 without any indication that this is a special case
        """),
        labels=["bug"],
    )
    issues.append(related_bug)

    # Create a documentation issue
    docs_issue = test_repo.create_issue(
        title="Improve calculator documentation",
        body=dedent("""
        ## Documentation Request

        The calculator documentation needs improvement.

        ### Areas to Improve
        - Add examples for each operation
        - Document error handling
        - Include usage patterns
        - Add type hints documentation

        ### Current State
        Documentation is minimal and lacks examples.
        """),
        labels=["documentation"],
    )
    issues.append(docs_issue)

    yield issues

    # Cleanup: Close all created issues
    for issue in issues:
        issue.edit(state="closed")


@pytest.fixture
async def test_prs(test_repo: Repository) -> AsyncGenerator[list[PullRequest], Any]:
    """Create test pull requests in the repository."""
    prs: list[PullRequest] = []

    existing_prs = test_repo.get_pulls(state="open")
    for pr in existing_prs:
        if pr.title.startswith("Removed"):
            continue
        pr.edit(state="closed", title="Removed", body="Removed")

    # Create a feature PR
    try:
        current_branch = test_repo.get_git_ref(ref="heads/feature/matrix-operations")
        current_branch.delete()
    except Exception as e:
        print(e)

    test_repo.create_git_ref(ref="refs/heads/feature/matrix-operations", sha=test_repo.get_branch("main").commit.sha)

    # Get the current calculator.py file
    calculator_file = test_repo.get_contents("calculator.py", ref="feature/matrix-operations")
    assert isinstance(calculator_file, ContentFile)
    calculator_file_sha = calculator_file.sha
    calculator_file_content = calculator_file.decoded_content.decode("utf-8")

    # Replace the calculator.py file with one that supports matrix operations
    append_matrix_operations = dedent("""
    def matrix_add(a, b):
        return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]
    """)

    # Update the calculator.py file
    test_repo.update_file(
        path="calculator.py",
        content=calculator_file_content + append_matrix_operations,
        sha=calculator_file_sha,
        message="Add matrix operations support",
        branch="feature/matrix-operations",
    )

    feature_pr = test_repo.create_pull(
        title="Add matrix operations support",
        body=dedent("""
        ## Changes

        - Added matrix addition and multiplication
        - Implemented matrix transposition
        - Added matrix determinant calculation
        - Added tests for new functionality

        ## Testing
        - [x] Unit tests added
        - [x] Integration tests added
        - [x] Documentation updated
        """),
        head="feature/matrix-operations",
        base="main",
    )
    prs.append(feature_pr)

    # Create a bug fix PR
    try:
        current_branch = test_repo.get_git_ref(ref="heads/fix/division-by-zero")
        current_branch.delete()
    except Exception as e:
        print(e)

    test_repo.create_git_ref(ref="refs/heads/fix/division-by-zero", sha=test_repo.get_branch("main").commit.sha)

    calculator_file = test_repo.get_contents("calculator.py", ref="fix/division-by-zero")
    assert isinstance(calculator_file, ContentFile)
    calculator_file_sha = calculator_file.sha
    calculator_file_content = calculator_file.decoded_content.decode("utf-8")

    append_division_by_zero_handling = dedent("""
    class DivisionByZeroError(Exception):
        pass

    def can_divide(a, b):
        'Check if division is possible.'
        return b != 0

    def safe_divide(a, b):
        'Divide a by b, raising DivisionByZeroError if b is 0. Run can_divide first to check if division is possible.'

        if not can_divide(a, b):
            raise DivisionByZeroError("Division by zero")
        return a / b

    """)

    test_repo.update_file(
        path="calculator.py",
        content=calculator_file_content + append_division_by_zero_handling,
        sha=calculator_file_sha,
        message="Fix division by zero handling",
        branch="fix/division-by-zero",
    )

    bug_pr = test_repo.create_pull(
        title="Fix division by zero handling",
        body=dedent("""
        ## Changes

        - Added proper error handling for division by zero
        - Implemented custom DivisionByZeroError
        - Added test cases for error handling
        - Updated documentation

        ## Testing
        - [x] Unit tests added
        - [x] Edge cases covered
        - [x] Error handling verified
        """),
        head="fix/division-by-zero",
        base="main",
    )
    prs.append(bug_pr)

    yield prs

    # Cleanup: Close all created PRs and delete branches
    for pr in prs:
        pr.edit(state="closed")
        try:
            git_ref = test_repo.get_git_ref(ref=f"refs/heads/{pr.head.ref}")
            git_ref.delete()
        except Exception as e:
            print(e)


def create_test_issue(repo: Repository, title: str, body: str, labels: list[str] | None = None) -> Issue:
    """Helper function to create a test issue."""
    return repo.create_issue(title=title, body=body, labels=labels or [])


class CaseInput(GitHubIssue):
    pass


judge = (
    LLMJudge(
        score={"evaluation_name": "investigation", "include_reason": True},
        include_input=True,
        rubric=evaluation_rubric(
            criteria="""The agent's message history confirms it used the handoff_to_code_agent tool to implement the code change.
            then it created a pull request to propose merging the changes into the main branch."""
        ),
    ),
)


async def test_implementation_cases(test_issues: list[Issue], test_prs: list[PullRequest], clone_repo: Path):
    issue: Issue = test_issues[0]

    async def run_implementation(case_input: CaseInput) -> AgentRunResult[str | Failure]:
        investigate_issue = GitHubIssue(
            issue_number=case_input.issue_number,
            owner=case_input.owner,
            repo=case_input.repo,
        )
        return await issue_driven_agent.run(
            user_prompt=f"The issue number for this task is {case_input.issue_number}. You must only search for open issues and open pull requests.",
            deps=IssueDrivenAgentInput(investigate_issue=investigate_issue, options=IssueDrivenAgentOptions(code_base=clone_repo)),
        )

    dataset = Dataset(
        evaluators=judge,
        cases=[
            Case[CaseInput, Any, Any](
                name="enhancement: Add support for custom model configurations",
                inputs=CaseInput(owner=issue.repository.owner.login, repo=issue.repository.name, issue_number=issue.number),
            ),
        ],
    )

    evaluation: EvaluationReport[CaseInput, Any, Any] = await dataset.evaluate(
        task=run_implementation,
        name="GitHub Agent Implementation",
    )

    assert_passed(evaluation_report=evaluation)
