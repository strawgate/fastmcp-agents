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
from pydantic import BaseModel
from pydantic_ai import RunContext
from pydantic_ai.agent import AgentRunResult
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge
from pydantic_evals.reporting import EvaluationReport

from fastmcp_agents.library.agents.github.agents.issue_driven_agent import (
    IssueDrivenAgentInput,
    IssueTriageAgentSettings,
    issue_driven_agent,
)
from fastmcp_agents.library.agents.github.agents.research_agent import ResearchAgentDependency, github_research_agent
from fastmcp_agents.library.agents.github.dependencies.result import AgentResult

from .conftest import assert_passed, evaluation_rubric

if TYPE_CHECKING:
    from github.GitRef import GitRef


@pytest.fixture
def github_client():
    """Create a GitHub client using the GITHUB_TOKEN environment variable."""
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN environment variable not set")
    return Github(token)


@pytest.fixture
async def search_open_only_please():
    """Persuade the research agent to only search for open issues and pull requests."""

    instructions = (
        "When searching for issues and pull requests, you must always search for only open issues and pull requests."
        "If you find a pull request or issue that is closed, you MUST ignore it."
        "To do this, you must set the `state` argument to `open` for all search tools: `state=open`"
    )

    @github_research_agent.instructions
    async def research_agent_instructions(ctx: RunContext[ResearchAgentDependency]) -> str:  # pyright: ignore[reportUnusedFunction]
        return instructions

    yield

    instructions = ""


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


@pytest.fixture(autouse=True)
def close_test_issues(test_repo: Repository):
    """Close all test issues."""
    existing_issues = test_repo.get_issues(state="open")

    for issue in existing_issues:
        issue.edit(state="closed", title="Removed", body="Removed")


@pytest.fixture
async def test_issues(test_repo: Repository, close_test_issues: None) -> AsyncGenerator[list[Issue], Any]:
    """Create test issues in the repository."""

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


@pytest.fixture(autouse=True)
def close_test_prs(test_repo: Repository):
    """Close all test pull requests."""
    existing_prs = test_repo.get_pulls(state="open")
    for pr in existing_prs:
        if pr.title.startswith("Removed"):
            continue
        pr.edit(state="closed", title="Removed", body="Removed")


@pytest.fixture
async def test_prs(test_repo: Repository, close_test_prs: None) -> AsyncGenerator[list[PullRequest], Any]:
    """Create test pull requests in the repository."""
    prs: list[PullRequest] = []

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


class CaseInput(BaseModel):
    owner: str
    repo: str
    issue_number: int
    instructions: str | None = None


async def run_evaluation(
    case: Case,
    clone_repo: Path,
    criteria: str | None = None,
    user_prompt: str | None = None,
) -> EvaluationReport[CaseInput, Any, Any]:
    base_criteria = """The Agent's message history confirms that it did not fabricate it's response.
    All information should be strongly rooted in either:
    1. Obvious Knowledge
    2. Provided Information
    3. Tool calls and responses

    Any response that is not based on the provided information or from Tool calls is considered fabrication.

    If the Agent performed invalid, failed, or excessive tool calls, it did not pass the criteria."""

    if criteria:
        criteria = f"{base_criteria}\n\n{criteria}"

    base_user_prompt = """
    Please handle the provided user reported GitHub issue.
    Please note, when searching for issues and pull requests, only search for open ones.
    If you handoff to other Agents, you must insist that all searches performed are ONLY for open issues and pull requests.
    """

    user_prompt = f"{user_prompt!s}\n\n{base_user_prompt}"

    judge = (
        LLMJudge(
            score={"evaluation_name": "investigation", "include_reason": True},
            include_input=True,
            rubric=evaluation_rubric(
                criteria=criteria or base_criteria,
            ),
        ),
    )

    dataset = Dataset(
        evaluators=judge,
        cases=[case],
    )

    async def run_implementation(case_input: CaseInput) -> AgentRunResult[AgentResult]:
        investigate_issue = IssueDrivenAgentInput(
            issue_owner=case_input.owner,
            issue_repo=case_input.repo,
            issue_number=case_input.issue_number,
            agent_settings=IssueTriageAgentSettings(
                code_base=clone_repo,
            ),
        )
        return await issue_driven_agent.run(
            user_prompt=user_prompt,
            deps=investigate_issue.to_deps(),
        )

    evaluation: EvaluationReport[CaseInput, Any, Any] = await dataset.evaluate(
        task=run_implementation,
        name="GitHub Agent Implementation",
    )

    return evaluation


@pytest.fixture
def matrix_operations_issue(test_repo: Repository, close_test_issues: None) -> Issue:
    return test_repo.create_issue(
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


@pytest.fixture
def matrix_operations_pr(test_repo: Repository, close_test_prs: None, matrix_operations_issue: Issue) -> PullRequest:
    # Create a feature PR
    force_create_github_branch(repository=test_repo, branch="feature/matrix-operations")

    # Get the current calculator.py file
    calculator_file_content: str = get_file_contents_str(repository=test_repo, path="calculator.py", ref="feature/matrix-operations")

    # Replace the calculator.py file with one that supports matrix operations
    append_matrix_operations: str = dedent("""
    def matrix_add(a, b):
        return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]
    """)

    # Update the calculator.py file
    update_file(
        repository=test_repo,
        ref="feature/matrix-operations",
        path="calculator.py",
        content=calculator_file_content + append_matrix_operations,
        message="Add matrix operations support",
    )

    issue_number = matrix_operations_issue.number

    return test_repo.create_pull(
        title="Add matrix operations support",
        body=dedent(f"""
        Fixes #{issue_number}

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


async def test_matrix_operations_issue(
    matrix_operations_issue: Issue, matrix_operations_pr: PullRequest, clone_repo: Path, search_open_only_please: None
):
    criteria = """The Agent notices that there is an open pull request that implements this feature and reports that fact
    to the user. The Agent attempts to implement the code change and completes the checklist items. The Agent does not lie
    about testing the changes (it has no ability to test the changes)."""

    case_input = CaseInput(
        owner=matrix_operations_issue.repository.owner.login,
        repo=matrix_operations_issue.repository.name,
        issue_number=matrix_operations_issue.number,
    )

    checkout_pr_branch(repo=clone_repo, pr=matrix_operations_pr)

    case = Case[CaseInput, Any, Any](name="enhancement: Add matrix operations support", inputs=case_input)

    evaluation: EvaluationReport[CaseInput, Any, Any] = await run_evaluation(case=case, clone_repo=clone_repo, criteria=criteria)

    assert_passed(evaluation_report=evaluation)


@pytest.fixture
def division_by_zero_issue(test_repo: Repository, close_test_issues: None) -> Issue:
    return test_repo.create_issue(
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


def division_by_zero_pr(test_repo: Repository, close_test_prs: None, division_by_zero_issue: Issue) -> PullRequest:
    force_create_github_branch(repository=test_repo, branch="fix/division-by-zero")

    calculator_file_content: str = get_file_contents_str(repository=test_repo, path="calculator.py", ref="fix/division-by-zero")

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

    update_file(
        repository=test_repo,
        ref="fix/division-by-zero",
        path="calculator.py",
        content=calculator_file_content + append_division_by_zero_handling,
        message="Fix division by zero handling",
    )

    return test_repo.create_pull(
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


async def test_division_by_zero_issue(
    division_by_zero_issue: Issue, division_by_zero_pr: PullRequest, clone_repo: Path, search_open_only_please: None
):
    evaluation: EvaluationReport[CaseInput, Any, Any] = await run_evaluation(
        Case[CaseInput, Any, Any](
            name="bug: Fix division by zero handling",
            inputs=CaseInput(
                owner=division_by_zero_issue.repository.owner.login,
                repo=division_by_zero_issue.repository.name,
                issue_number=division_by_zero_issue.number,
            ),
        ),
        clone_repo=clone_repo,
        criteria="""The Agent identifies that dividing by zero is a special case and implements new error handling for
        that case.""",
    )

    assert_passed(evaluation_report=evaluation)


@pytest.fixture
def invalid_bug_report_issue(test_repo: Repository, close_test_issues: None) -> Issue:
    return test_repo.create_issue(
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


async def test_invalid_bug_report(invalid_bug_report_issue: Issue, clone_repo: Path, search_open_only_please: None):
    evaluation: EvaluationReport[CaseInput, Any, Any] = await run_evaluation(
        Case[CaseInput, Any, Any](
            name="bug: Calculator incorrectly returns 0 for multiplication by zero",
            inputs=CaseInput(
                owner=invalid_bug_report_issue.repository.owner.login,
                repo=invalid_bug_report_issue.repository.name,
                issue_number=invalid_bug_report_issue.number,
            ),
        ),
        clone_repo=clone_repo,
        criteria="""The Agent notices that the bug report is invalid and reports that fact to the user.
        The Agent does not attempt to implement the code change.""",
    )

    assert_passed(evaluation_report=evaluation)


@pytest.fixture
def documentation_request_issue(test_repo: Repository, close_test_issues: None) -> Issue:
    return test_repo.create_issue(
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


async def test_documentation_request(documentation_request_issue: Issue, clone_repo: Path, search_open_only_please: None):
    evaluation: EvaluationReport[CaseInput, Any, Any] = await run_evaluation(
        Case[CaseInput, Any, Any](
            name="documentation: Improve calculator documentation",
            inputs=CaseInput(
                owner=documentation_request_issue.repository.owner.login,
                repo=documentation_request_issue.repository.name,
                issue_number=documentation_request_issue.number,
            ),
        ),
        clone_repo=clone_repo,
        criteria="""The Agent notices that the documentation request is valid and implements the requested changes.""",
    )

    assert_passed(evaluation_report=evaluation)


async def test_review_matrix_operations_pr(matrix_operations_pr: PullRequest, clone_repo: Path, search_open_only_please: None):
    evaluation: EvaluationReport[CaseInput, Any, Any] = await run_evaluation(
        Case[CaseInput, Any, Any](
            name="enhancement: Add matrix operations support",
            inputs=CaseInput(
                owner=matrix_operations_pr.head.repo.owner.login,
                repo=matrix_operations_pr.head.repo.name,
                issue_number=matrix_operations_pr.number,
                instructions="""Please review the Pull Request and provide feedback on the proposed changes.""",
            ),
        ),
        clone_repo=clone_repo,
        criteria="""The Agent notices that the pull request implements only some of the requested changes and reports that fact to the user.
        The Agent does not attempt to implement the code change.""",
    )

    assert_passed(evaluation_report=evaluation)


async def test_review_division_by_zero_pr(division_by_zero_pr: PullRequest, clone_repo: Path, search_open_only_please: None):
    evaluation: EvaluationReport[CaseInput, Any, Any] = await run_evaluation(
        Case[CaseInput, Any, Any](
            name="bug: Fix division by zero handling",
            inputs=CaseInput(
                owner=division_by_zero_pr.head.repo.owner.login,
                repo=division_by_zero_pr.head.repo.name,
                issue_number=division_by_zero_pr.number,
            ),
        ),
        clone_repo=clone_repo,
        criteria="""The Agent notices that the pull request fixes the division by zero issue but does
        not add the mentioned unit tests, edge cases, or error handling.""",
    )

    assert_passed(evaluation_report=evaluation)
