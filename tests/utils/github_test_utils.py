import os
from collections.abc import Generator
from typing import Any

import pytest
from github import Github
from github.Issue import Issue
from github.PullRequest import PullRequest


@pytest.fixture
def github_client():
    """Create a GitHub client using the GITHUB_TOKEN environment variable."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN environment variable not set")
    return Github(token)


@pytest.fixture
def test_repo(github_client):
    """Get the test repository."""
    return github_client.get_repo("strawgate/fastmcp-agents-tests-e2e")


@pytest.fixture
def test_issues(test_repo) -> Generator[list[Issue], Any, Any]:
    """Create test issues in the repository."""
    issues = []

    # Create a feature request
    feature_request = test_repo.create_issue(
        title="Add support for custom model configurations",
        body="""
        ## Feature Request

        It would be great to have support for custom model configurations in the agent.

        ### Use Case
        - Allow users to specify custom model parameters
        - Support different model providers
        - Enable fine-tuning options

        ### Additional Context
        This would make the agent more flexible and adaptable to different use cases.
        """,
        labels=["enhancement"],
    )
    issues.append(feature_request)

    # Create a bug report
    bug_report = test_repo.create_issue(
        title="Agent fails to handle empty response from model",
        body="""
        ## Bug Report

        The agent crashes when the model returns an empty response.

        ### Steps to Reproduce
        1. Send a request to the agent
        2. Model returns empty response
        3. Agent crashes with KeyError

        ### Expected Behavior
        Agent should handle empty responses gracefully

        ### Actual Behavior
        Agent crashes with KeyError: 'content'
        """,
        labels=["bug"],
    )
    issues.append(bug_report)

    # Create a documentation issue
    docs_issue = test_repo.create_issue(
        title="Improve API documentation",
        body="""
        ## Documentation Request

        The API documentation needs improvement.

        ### Areas to Improve
        - Add more examples
        - Document all parameters
        - Include error handling examples

        ### Current State
        Documentation is minimal and lacks examples.
        """,
        labels=["documentation"],
    )
    issues.append(docs_issue)

    yield issues

    # Cleanup: Close all created issues
    for issue in issues:
        issue.edit(state="closed")


@pytest.fixture
def test_prs(test_repo) -> Generator[list[PullRequest], Any, Any]:
    """Create test pull requests in the repository."""
    prs = []

    # Create a feature PR
    test_repo.create_git_ref(ref="refs/heads/feature/custom-models", sha=test_repo.get_branch("main").commit.sha)

    feature_pr = test_repo.create_pull(
        title="Add support for custom model configurations",
        body="""
        ## Changes

        - Added support for custom model configurations
        - Implemented model parameter validation
        - Added tests for new functionality

        ## Testing
        - [x] Unit tests added
        - [x] Integration tests added
        - [x] Documentation updated
        """,
        head="feature/custom-models",
        base="main",
    )
    prs.append(feature_pr)

    # Create a bug fix PR
    test_repo.create_git_ref(ref="refs/heads/fix/empty-response", sha=test_repo.get_branch("main").commit.sha)

    bug_pr = test_repo.create_pull(
        title="Fix handling of empty model responses",
        body="""
        ## Changes

        - Added null check for model responses
        - Implemented graceful error handling
        - Added test cases for empty responses

        ## Testing
        - [x] Unit tests added
        - [x] Edge cases covered
        - [x] Error handling verified
        """,
        head="fix/empty-response",
        base="main",
    )
    prs.append(bug_pr)

    yield prs

    # Cleanup: Close all created PRs and delete branches
    for pr in prs:
        pr.edit(state="closed")
        test_repo.get_git_ref(f"heads/{pr.head.ref}").delete()


def create_test_issue(repo, title: str, body: str, labels: list[str] | None = None) -> Issue:
    """Helper function to create a test issue."""
    return repo.create_issue(title=title, body=body, labels=labels or [])


def create_test_pr(repo, title: str, body: str, branch_name: str, labels: list[str] | None = None) -> PullRequest:
    """Helper function to create a test PR."""
    # Create branch
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=repo.get_branch("main").commit.sha)

    # Create PR
    return repo.create_pull(title=title, body=body, head=branch_name, base="main", labels=labels or [])
