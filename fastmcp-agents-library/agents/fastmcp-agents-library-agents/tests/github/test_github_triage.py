from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Repository import Repository
from pydantic import BaseModel
from pydantic_ai import RunContext
from pydantic_ai.run import AgentRunResult
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge
from pydantic_evals.reporting import EvaluationReport

from fastmcp_agents.library.agents.github.agents.issue_driven_agent import (
    IssueDrivenAgentInput,
    IssueTriageAgentSettings,
    IssueTriageAgentState,
    issue_driven_agent,
)
from fastmcp_agents.library.agents.github.agents.research_agent import ResearchAgentDependency, github_research_agent
from fastmcp_agents.library.agents.github.dependencies.result import AgentResult
from tests.conftest import AgentRunInput, evaluate_agent_case, evaluation_rubric
from tests.github.conftest import (
    checkout_pr_branch,
    force_create_github_branch,
    get_file_contents_str,
    update_file,
)

BASE_INSTRUCTIONS = """
Please handle the provided user reported GitHub issue.
Please note, when searching for issues and pull requests, only search for open ones.
If you handoff to other Agents, you must insist that all searches performed are ONLY for open issues and pull requests.
"""


def issue_driven_case(
    issue: Issue, clone_repo: Path, read_only: bool = False, custom_instructions: str | None = None
) -> Case[AgentRunInput[IssueTriageAgentState], Any, Any]:
    return AgentRunInput[IssueTriageAgentState](
        user_prompt=custom_instructions or BASE_INSTRUCTIONS,
        deps=IssueDrivenAgentInput.from_issue(
            issue=issue,
            agent_settings=IssueTriageAgentSettings(
                code_base=clone_repo,
                read_only=read_only,
            ),
        ).to_deps(),
    ).to_case(name=f"{issue.title}: {issue.body}")


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


async def test_matrix_operations_issue_ro(
    matrix_operations_issue: Issue, matrix_operations_pr: PullRequest, clone_repo: Path, search_open_only_please: None
):
    checkout_pr_branch(repo=clone_repo, pr=matrix_operations_pr)

    criteria = (
        "The Agent notices that there is an open pull request that implements this feature and reports that fact"
        "to the user. The Agent mentions that the pull request is incomplete and recommends completing it. The Agent"
        "does not attempt to implement the code change and does not indicate that it could or did."
    )

    await evaluate_agent_case(
        agent=issue_driven_agent,
        case=issue_driven_case(issue=matrix_operations_issue, clone_repo=clone_repo, read_only=True),
        criteria=criteria,
    )


async def test_matrix_operations_issue_rw(
    matrix_operations_issue: Issue, matrix_operations_pr: PullRequest, clone_repo: Path, search_open_only_please: None
):
    checkout_pr_branch(repo=clone_repo, pr=matrix_operations_pr)

    criteria = (
        "The Agent notices that there is an open pull request that implements this feature and reports that fact"
        "to the user. The Agent does not attempt to implement the code change even though it could."
    )

    await evaluate_agent_case(
        agent=issue_driven_agent,
        case=issue_driven_case(issue=matrix_operations_issue, clone_repo=clone_repo),
        criteria=criteria,
    )


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


@pytest.fixture
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


async def test_division_by_zero_issue_ro(
    division_by_zero_issue: Issue, division_by_zero_pr: PullRequest, clone_repo: Path, search_open_only_please: None
):
    criteria = (
        "The Agent identifies that dividing by zero is a special case and that there is an open pull request"
        "that implements the fix. The Agent notices that tasks on the pull request like writing tests are incomplete"
        "and recommends completing them or that the implementation does not match the description of the pull request."
    )

    await evaluate_agent_case(
        agent=issue_driven_agent,
        case=issue_driven_case(issue=division_by_zero_issue, clone_repo=clone_repo, read_only=True),
        criteria=criteria,
    )


async def test_division_by_zero_issue_rw(
    division_by_zero_issue: Issue, division_by_zero_pr: PullRequest, clone_repo: Path, search_open_only_please: None
):
    criteria = (
        "The Agent identifies that dividing by zero is a special case and that there is an open pull request"
        "that implements the fix. The Agent does not attempt to implement the code change even if it could"
        "but recommends completing the open pull request."
    )

    await evaluate_agent_case(
        agent=issue_driven_agent,
        case=issue_driven_case(issue=division_by_zero_issue, clone_repo=clone_repo),
        criteria=criteria,
    )


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


async def test_invalid_bug_report_issue_ro(invalid_bug_report_issue: Issue, clone_repo: Path, search_open_only_please: None):
    criteria = (
        "The Agent notices that the bug report is invalid and reports that fact to the user. The Agent does not attempt"
        "to implement the code change."
    )

    await evaluate_agent_case(
        agent=issue_driven_agent,
        case=issue_driven_case(issue=invalid_bug_report_issue, clone_repo=clone_repo, read_only=True),
        criteria=criteria,
    )


async def test_invalid_bug_report_issue_rw(invalid_bug_report_issue: Issue, clone_repo: Path, search_open_only_please: None):
    criteria = (
        "The Agent notices that the bug report is invalid and reports that fact to the user. The Agent does not attempt"
        "to implement the code change."
    )

    await evaluate_agent_case(
        agent=issue_driven_agent,
        case=issue_driven_case(issue=invalid_bug_report_issue, clone_repo=clone_repo),
        criteria=criteria,
    )


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


async def test_documentation_request_ro(documentation_request_issue: Issue, clone_repo: Path, search_open_only_please: None):
    criteria = "The Agent notices that the documentation request is valid and implements the requested changes."

    await evaluate_agent_case(
        agent=issue_driven_agent,
        case=issue_driven_case(issue=documentation_request_issue, clone_repo=clone_repo, read_only=True),
        criteria=criteria,
    )


async def test_documentation_request_rw(documentation_request_issue: Issue, clone_repo: Path, search_open_only_please: None):
    criteria = "The Agent notices that the documentation request is valid and implements the requested changes."

    await evaluate_agent_case(
        agent=issue_driven_agent,
        case=issue_driven_case(issue=documentation_request_issue, clone_repo=clone_repo),
        criteria=criteria,
    )


async def test_review_matrix_operations_pr_ro(matrix_operations_pr: PullRequest, clone_repo: Path, search_open_only_please: None):
    criteria = (
        "The Agent notices that the pull request implements only some of the requested changes and reports that fact to the user."
        "The Agent does not attempt to implement the code change."
    )

    await evaluate_agent_case(
        agent=issue_driven_agent,
        case=issue_driven_case(issue=matrix_operations_pr.as_issue(), clone_repo=clone_repo, read_only=True),
        criteria=criteria,
    )


async def test_review_matrix_operations_pr_rw(matrix_operations_pr: PullRequest, clone_repo: Path, search_open_only_please: None):
    criteria = (
        "The Agent notices that the pull request implements only some of the requested changes and reports that fact to the user."
        "The Agent does not attempt to implement the code change."
    )

    await evaluate_agent_case(
        agent=issue_driven_agent,
        case=issue_driven_case(issue=matrix_operations_pr.as_issue(), clone_repo=clone_repo),
        criteria=criteria,
    )


async def test_review_division_by_zero_pr_ro(division_by_zero_pr: PullRequest, clone_repo: Path, search_open_only_please: None):
    criteria = (
        "The Agent notices that the pull request fixes the division by zero issue but does"
        "not add the mentioned unit tests, edge cases, or error handling."
    )

    await evaluate_agent_case(
        agent=issue_driven_agent,
        case=issue_driven_case(issue=division_by_zero_pr.as_issue(), clone_repo=clone_repo, read_only=True),
        criteria=criteria,
    )


async def test_review_division_by_zero_pr_rw(division_by_zero_pr: PullRequest, clone_repo: Path, search_open_only_please: None):
    criteria = (
        "The Agent notices that the pull request fixes the division by zero issue but does"
        "not add the mentioned unit tests, edge cases, or error handling. The Agent does not attempt to implement"
        "the code change even though it could."
    )

    await evaluate_agent_case(
        agent=issue_driven_agent,
        case=issue_driven_case(issue=division_by_zero_pr.as_issue(), clone_repo=clone_repo),
        criteria=criteria,
    )
