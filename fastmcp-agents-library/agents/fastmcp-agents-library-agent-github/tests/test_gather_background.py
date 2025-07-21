import json
from typing import TYPE_CHECKING, Any

import pytest
from fastmcp.client.client import CallToolResult
from mcp.types import TextContent

from fastmcp_agents.library.agent.github.gather_background import GitHubIssueBackgroundAgent, GitHubIssueSummary, server

if TYPE_CHECKING:
    from fastmcp_agents.core.agents.base import DefaultFailureModel


def test_init():
    assert server is not None


def extract_text_from_call_tool_result(call_tool_result: CallToolResult) -> str:
    content = call_tool_result.content

    for part in content:
        if isinstance(part, TextContent):
            return part.text

    msg = "No text content found"
    raise ValueError(msg)


def extract_structured_content_from_call_tool_result(call_tool_result: CallToolResult) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    text = extract_text_from_call_tool_result(call_tool_result)
    structured_content: dict[str, Any] | None = json.loads(text)  # pyright: ignore[reportAny]

    if not isinstance(structured_content, dict):
        msg = "Structured content is not a dictionary"
        raise TypeError(msg)

    return structured_content


@pytest.mark.asyncio
@pytest.mark.not_on_ci
async def test_simple_background():
    agent = GitHubIssueBackgroundAgent()

    result: GitHubIssueSummary | DefaultFailureModel = await agent(
        issue_repository_owner="strawgate", issue_repository="fastmcp-agents", issue_number=5
    )

    assert isinstance(result, GitHubIssueSummary)

    assert result.issue_title == "Publish a docker container image, or maybe just a Dockerfile example"
    assert result.issue_number == 5

    assert len(result.detailed_summary) > 10

    # assert "closed" in result.detailed_summary.lower() or "resolved" in result.detailed_summary.lower()

    assert result.related_issues is not None
    assert len(result.related_issues) > 0
