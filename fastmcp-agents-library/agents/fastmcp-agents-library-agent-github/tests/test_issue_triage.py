from pathlib import Path

import pytest
from git import Repo

from fastmcp_agents.library.agent.github.investigate_issue import investigate_github_issue
from fastmcp_agents.library.agent.github.shared.git import get_repo_url


@pytest.mark.asyncio
@pytest.mark.skip_on_ci
async def test_simple_traige():
    issue_summary, investigation_response, issue_response = await investigate_github_issue(
        owner="strawgate",
        repo="fastmcp-agents",
        issue_number=5,
        reply_to_issue=False,
    )

    assert issue_summary is not None
    assert investigation_response is not None
    assert issue_response is None

    assert len(issue_summary.detailed_summary) > 10
    assert len(investigation_response.findings) > 0
    assert len(investigation_response.recommendations) > 0


@pytest.fixture
def beats_repository() -> Path:
    repo_url = get_repo_url(owner="elastic", repository="beats")
    temp_dir = Path.cwd() / "playground"
    if not temp_dir.exists():
        temp_dir.mkdir()

    beats_dir = temp_dir / "beats"

    if beats_dir.exists():
        return beats_dir

    print(f"Cloning {repo_url} to {beats_dir}")

    Repo.clone_from(url=str(repo_url), to_path=beats_dir, single_branch=True, depth=1)

    print(f"Cloning {repo_url} to {beats_dir} complete")

    return beats_dir


@pytest.mark.asyncio
@pytest.mark.skip_on_ci
async def test_private_beats_traige(beats_repository: Path):
    issue_summary, investigation_response, issue_response = await investigate_github_issue(
        owner="elastic",
        repo="beats",
        code_path=beats_repository,
        issue_number=45364,
        reply_to_owner="elastic",
        reply_to_repo="private-repo-triage",
        reply_to_issue_number=39,
        reply_to_issue=True,
    )

    assert issue_summary is not None
    assert investigation_response is not None
    assert issue_response is not None

    assert len(investigation_response.findings) > 0
    assert len(investigation_response.recommendations) > 0
