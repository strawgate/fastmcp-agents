import tempfile
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.tools import Tool
from fastmcp_agents.library.agents.github.agents import (
    comment_on_github_issue_raw,
    gather_github_issue_background_raw,
)
from fastmcp_agents.library.agents.github.models import GitHubIssueSummary
from fastmcp_agents.library.agents.simple_code.agents import investigate_code_repository_raw
from fastmcp_agents.library.agents.simple_code.models import InvestigationResult
from git.repo import Repo
from pydantic_ai.agent import AgentRunResult


async def triage_github_issue_raw(
    owner: str, repo: str, issue_number: int
) -> tuple[AgentRunResult[GitHubIssueSummary], AgentRunResult[InvestigationResult], AgentRunResult[str]]:
    background: AgentRunResult[GitHubIssueSummary] = await gather_github_issue_background_raw(
        owner=owner, repo=repo, issue_number=issue_number
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        clone: Repo = Repo.clone_from(url=f"https://github.com/{owner}/{repo}.git", to_path=temp_dir, depth=1, single_branch=True)

        clone_path: Path = Path(clone.working_dir)

        investigation: AgentRunResult[InvestigationResult] = await investigate_code_repository_raw(
            task=background.output.detailed_summary, code_repository=clone_path
        )

        response: AgentRunResult[str] = await comment_on_github_issue_raw(
            owner=owner, repo=repo, issue_number=issue_number, information=[background.output, investigation.output]
        )

        return background, investigation, response


async def triage_github_issue(owner: str, repo: str, issue_number: int) -> str:
    return (await triage_github_issue_raw(owner=owner, repo=repo, issue_number=issue_number))[2].output


triage_github_issue_tool = Tool.from_function(fn=triage_github_issue)


async def private_fork_triage_github_issue_raw(
    public_owner: str,
    public_repo: str,
    public_issue_number: int,
    private_owner: str,
    private_repo: str,
    private_issue_number: int,
) -> tuple[AgentRunResult[GitHubIssueSummary], AgentRunResult[InvestigationResult], AgentRunResult[str]]:
    background: AgentRunResult[GitHubIssueSummary] = await gather_github_issue_background_raw(
        owner=public_owner, repo=public_repo, issue_number=public_issue_number
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        clone: Repo = Repo.clone_from(
            url=f"https://github.com/{public_owner}/{public_repo}.git", to_path=temp_dir, depth=1, single_branch=True
        )

        clone_path: Path = Path(clone.working_dir)

        investigation: AgentRunResult[InvestigationResult] = await investigate_code_repository_raw(
            task=background.output.detailed_summary, code_repository=clone_path
        )

        response: AgentRunResult[str] = await comment_on_github_issue_raw(
            owner=private_owner,
            repo=private_repo,
            issue_number=private_issue_number,
            information=[
                background.output,
                investigation.output,
            ],
        )

        return background, investigation, response


async def private_fork_triage_github_issue(
    public_owner: str,
    public_repo: str,
    public_issue_number: int,
    private_owner: str,
    private_repo: str,
    private_issue_number: int,
) -> str:
    return (
        await private_fork_triage_github_issue_raw(
            public_owner=public_owner,
            public_repo=public_repo,
            public_issue_number=public_issue_number,
            private_owner=private_owner,
            private_repo=private_repo,
            private_issue_number=private_issue_number,
        )
    )[2].output


private_fork_triage_github_issue_tool = Tool.from_function(fn=private_fork_triage_github_issue)

server = FastMCP[None](name="github-issue-triage", tools=[triage_github_issue_tool, private_fork_triage_github_issue_tool])


def run():
    server.run()


def run_sse():
    server.run(transport="sse")
