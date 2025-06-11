import os
import subprocess
from collections.abc import AsyncGenerator
from pathlib import Path
from textwrap import dedent
from typing import Any
from unittest.mock import MagicMock

import pytest
from github import Github
from github.ContentFile import ContentFile
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.PullRequestReview import PullRequestReview
from github.Repository import Repository

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.conversation.utils import get_tool_calls_from_conversation
from tests.conftest import evaluate_with_criteria


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
async def test_issues(test_repo) -> AsyncGenerator[list[Issue], Any]:
    """Create test issues in the repository."""
    issues = []

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
    prs = []

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
        test_repo.get_git_ref(ref=f"refs/heads/{pr.head.ref}").delete()


def create_test_issue(repo, title: str, body: str, labels: list[str] | None = None) -> Issue:
    """Helper function to create a test issue."""
    return repo.create_issue(title=title, body=body, labels=labels or [])


def create_test_pr(repo, title: str, body: str, branch_name: str, labels: list[str] | None = None) -> PullRequest:
    """Helper function to create a test PR."""
    # Create branch
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=repo.get_branch("main").commit.sha)

    # Create PR
    return repo.create_pull(title=title, body=body, head=branch_name, base="main", labels=labels or [])


def get_pr_comments(pr: PullRequest) -> list[str]:
    """Helper function to get all comments from a GitHub PR."""
    return [comment.body for comment in pr.get_issue_comments()]


def get_pr_reviews(pr: PullRequest) -> list[PullRequestReview]:
    """Helper function to get all reviews from a GitHub PR."""
    return list(pr.get_reviews())


def get_pr_review_comments(pr: PullRequest) -> list[str]:
    """Helper function to get all review comments from a GitHub PR."""
    return [comment.body for comment in pr.get_review_comments()]


def get_issue_comments(issue: Issue) -> list[str]:
    """Helper function to get all comments from a GitHub issue.

    Args:
        issue: The GitHub issue to get comments from

    Returns:
        A list of comment bodies as strings
    """
    return [comment.body for comment in issue.get_comments()]


@pytest.fixture
def server_config_name():
    return "flow_github-triage"


@pytest.fixture
def project_in_dir(temp_working_dir: Path):
    # Clone the test repository
    repo_url = "https://github.com/strawgate/fastmcp-agents-tests-e2e.git"
    project_dir = temp_working_dir / "test_project"
    subprocess.run(["git", "clone", repo_url, project_dir], check=True)
    return project_dir


class TestGitHubTriageAgent:
    @pytest.fixture
    def agent_name(self):
        return "triage_github_feature_request"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the feature request was properly analyzed
        2. that potential duplicates were identified
        3. that related issues were found
        4. that relevant code sections were identified
        5. that a clear triage comment was posted

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_feature_request_triage(self, project_in_dir: Path, agent: CuratorAgent, test_issues):
        # Use the first issue (feature request) from the test issues
        feature_request = test_issues[0]

        task = f"""
        You are a GitHub triage agent for the calculator project in repository strawgate/fastmcp-agents-tests-e2e.
        The project is a Python calculator implementation with basic arithmetic operations and history tracking.
        The repository has been cloned to {project_in_dir} for your use.

        IMPORTANT: When searching for related issues, you MUST ONLY consider OPEN issues. Do not include closed issues in your analysis.

        1. Analyze the feature request in issue #{feature_request.number} in repository strawgate/fastmcp-agents-tests-e2e
        2. Identify any potential duplicates or related issues (ONLY consider currently OPEN issues)
        3. Find relevant code sections that would need to be modified
        4. Post a triage comment on the issue with your findings
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        # Verify that the agent posted a comment
        comments = get_issue_comments(feature_request)
        assert len(comments) > 0, "Agent did not post any comments on the issue"

        return agent, task, result, conversation

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the issue was properly identified as unrelated to the repository
        2. that the main response clearly indicated the issue is unrelated
        3. that the agent explained its reasoning
        4. that the agent suggested what would help clarify the situation

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_triage_unrelated_issue(self, project_in_dir: Path, agent: CuratorAgent, github_client):
        # Create an unrelated issue
        issue = create_test_issue(
            github_client.get_repo("strawgate/fastmcp-agents-tests-e2e"),
            title="Unrelated issue",
            body="This is an issue that is not related to the calculator project.",
        )

        task = f"""
        You are a GitHub triage agent for the calculator project in repository strawgate/fastmcp-agents-tests-e2e.
        The project is a Python calculator implementation with basic arithmetic operations and history tracking.
        The repository has been cloned to {project_in_dir} for your use.

        IMPORTANT: When asking for issues summarizes or other items from GitHub you must include instructions to
        only search for OPEN issues. Do not include closed issues in your analysis.

        1. Analyze issue #{issue.number} in repository strawgate/fastmcp-agents-tests-e2e
        2. Determine if it is related to the calculator project
        3. If unrelated, explain why and suggest what would help clarify the situation
        4. Post a triage comment on the issue with your findings
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        # Verify that the agent posted a comment
        comments = get_issue_comments(issue)
        assert len(comments) > 0, "Agent did not post any comments on the issue"

        # Verify that appropriate tools were called
        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        return agent, task, result, conversation


class TestGitHubBugReportAgent:
    @pytest.fixture
    def agent_name(self):
        return "triage_github_bug_report"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the bug report was properly analyzed
        2. that potential duplicates were identified
        3. that related issues were found
        4. that relevant code sections were identified
        5. that a clear triage comment was posted on the github issue

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_bug_report_triage(self, project_in_dir: Path, agent: CuratorAgent, test_issues):
        # Use the second issue (bug report) from the test issues
        bug_report = test_issues[1]

        task = f"""
        You are a GitHub triage agent for the calculator project in repository strawgate/fastmcp-agents-tests-e2e.
        The project is a Python calculator implementation with basic arithmetic operations and history tracking.
        The repository has been cloned to {project_in_dir} for your use.

        IMPORTANT: When asking for issues summarizes or other items from GitHub you must include instructions to
        only search for OPEN issues.
        Do not include closed issues in your analysis.

        1. Analyze the bug report in issue #{bug_report.number} in repository strawgate/fastmcp-agents-tests-e2e
        2. Identify any potential duplicates or related issues (ONLY consider currently OPEN issues)
        3. Find relevant code sections that would need to be modified
        4. Post a triage comment on the issue with your findings
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        # Verify that the agent posted a comment
        comments = get_issue_comments(bug_report)
        assert len(comments) > 0, "Agent did not post any comments on the issue"

        # Verify that appropriate tools were called
        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        return agent, task, result, conversation


class TestGitHubIssueInvestigationAgent:
    @pytest.fixture
    def agent_name(self):
        return "investigate_github_issue"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the issue was thoroughly investigated
        2. that relevant code paths were identified
        3. that bug conditions were documented
        4. that test cases were proposed
        5. that a detailed analysis was posted on the github issue

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_issue_investigation(self, project_in_dir: Path, agent: CuratorAgent, test_issues):
        # Use the bug report issue for investigation
        bug_report = test_issues[1]

        task = f"""
        You are a GitHub issue investigation agent for the calculator project in repository strawgate/fastmcp-agents-tests-e2e.
        The project is a Python calculator implementation with basic arithmetic operations and history tracking.
        The repository has been cloned to {project_in_dir} for your use.

        IMPORTANT: When asking for issues summarizes or other items from GitHub you must include instructions to
        only search for OPEN issues.
        Do not include closed issues in your analysis.

        1. Thoroughly investigate the bug report in issue #{bug_report.number} in repository strawgate/fastmcp-agents-tests-e2e
        2. Document code paths and conditions in the calculator implementation
        3. Identify any related issues (ONLY consider currently OPEN issues)
        4. Propose test cases to verify the bug
        5. Post a detailed analysis on the issue
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        # Verify that the agent posted a comment
        comments = get_issue_comments(bug_report)
        assert len(comments) > 0, "Agent did not post any comments on the issue"

        # Verify that appropriate tools were called
        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        potential_calls = ["ask_github_agent", "summarize_github_issue"]
        assert any(call in tool_call_names for call in potential_calls)

        return agent, task, result, conversation


class TestGitHubSolutionProposalAgent:
    @pytest.fixture
    def agent_name(self):
        return "propose_solution_for_github_issue"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the issue was thoroughly understood
        2. that a solution was proposed
        3. that code changes were detailed
        4. that test cases were included
        5. that a comprehensive solution was posted on the github issue

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_solution_proposal(self, project_in_dir: Path, agent: CuratorAgent, test_issues):
        # Use the bug report issue for solution proposal
        bug_report = test_issues[1]

        task = f"""
        You are a GitHub solution proposal agent for the calculator project in repository strawgate/fastmcp-agents-tests-e2e.
        The project is a Python calculator implementation with basic arithmetic operations and history tracking.
        The repository has been cloned to {project_in_dir} for your use.

        IMPORTANT: When asking for issues summarizes or other items from GitHub you must include instructions to
        only search for OPEN issues.
        Do not include closed issues in your analysis.

        1. Understand the bug report in issue #{bug_report.number} in repository strawgate/fastmcp-agents-tests-e2e
        2. Check for any related issues (ONLY consider currently OPEN issues)
        3. Propose a solution with code changes
        4. Include test cases
        5. Post a comprehensive solution on the issue
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        # Verify that the agent posted a comment
        comments = get_issue_comments(bug_report)
        assert len(comments) > 0, "Agent did not post any comments on the issue"

        # Verify that appropriate tools were called
        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        return agent, task, result, conversation


class TestGitHubPRReviewAgent:
    @pytest.fixture
    def agent_name(self):
        return "perform_pr_code_review"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the PR was thoroughly reviewed
        2. that the Agent noticed there were no tests added
        3. that improvements were suggested
        5. that a comprehensive review was posted on the github issue

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_pr_review(self, project_in_dir: Path, agent: CuratorAgent, test_prs: list[PullRequest]):
        # Use the bug fix PR for review
        bug_pr = test_prs[1]

        task = f"""
        You are a GitHub PR review agent for the calculator project in repository strawgate/fastmcp-agents-tests-e2e.
        The project is a Python calculator implementation with basic arithmetic operations and history tracking.
        The repository has been cloned to {project_in_dir} for your use.

        1. Review PR #{bug_pr.number} in repository strawgate/fastmcp-agents-tests-e2e thoroughly
        2. Check for any related open issues that this PR might address
        3. Suggest improvements to the Pull Request focusing on the code docs and tests
        4. Post a comprehensive Pull Request Review on the GitHub PR with your findings
        5. Call report success with the link to the PR review
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        # Verify that the agent posted a comment
        reviews = get_pr_reviews(bug_pr)
        assert len(reviews) > 0, "Agent did not post any reviews on the PR"

        # Verify that appropriate tools were called
        potential_calls = ["ask_code_agent", "ask_github_agent"]
        assert any(call in tool_call_names for call in potential_calls)

        return agent, task, result, conversation


class TestGitHubPRUpdateAgent:
    @pytest.fixture
    def agent_name(self):
        return "update_pr_with_code_or_docs"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the PR was properly updated
        2. that code changes were implemented
        3. that documentation was updated
        4. that tests were included if needed
        5. that changes were properly committed on the branch and a comment was posted on the PR

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_pr_update(self, project_in_dir: Path, agent: CuratorAgent, test_prs):
        # Use the feature PR for updates
        feature_pr = test_prs[0]

        task = f"""
        You are a GitHub PR update agent for the calculator project in repository strawgate/fastmcp-agents-tests-e2e.
        The project is a Python calculator implementation with basic arithmetic operations and history tracking.
        The repository has been cloned to {project_in_dir} for your use.

        1. Update PR #{feature_pr.number} in repository strawgate/fastmcp-agents-tests-e2e with requested changes
        2. Check for any related open issues that this PR update might affect
        3. Update documentation for the calculator implementation
        4. Add tests if needed
        5. Commit and push changes
        6. Post a comment on the GitHub PR with the changes you made
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        # Verify that the agent posted a comment
        comments = get_issue_comments(feature_pr)
        assert len(comments) > 0, "Agent did not post any comments on the PR"

        # Verify that appropriate tools were called
        potential_calls = ["ask_code_agent", "ask_github_agent"]
        assert any(call in tool_call_names for call in potential_calls)

        return agent, task, result, conversation
