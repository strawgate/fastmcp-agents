import pytest

from fastmcp_agents.library.agent.github.investigate_issue import investigate_github_issue


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_private_beats_traige():

    issue_summary, investigation_response, issue_response = await investigate_github_issue(
        owner="elastic",
        repo="private-repo-triage",
        code_owner="elastic",
        code_repo="beats",
        issue_number=39,
        reply_to_issue=True
    )

    assert issue_summary is not None
    assert investigation_response is not None
    assert issue_response is None

    assert len(investigation_response.findings) > 0
    assert len(investigation_response.recommendations) > 0
