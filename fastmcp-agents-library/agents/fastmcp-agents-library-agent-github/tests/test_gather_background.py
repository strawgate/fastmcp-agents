import json
from typing import Any

import pytest
from fastmcp.client.client import CallToolResult
from mcp.types import TextContent

from fastmcp_agents.library.agent.github.gather_background import GitHubIssueSummary, gather_background, server


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
@pytest.mark.skip_on_ci
async def test_simple_background():

    result = await gather_background(repo="fastmcp-agents", owner="strawgate", issue_number=5)

    assert isinstance(result, GitHubIssueSummary)

    assert result.issue_title == "Publish a docker container image, or maybe just a Dockerfile example"
    assert result.issue_number == 5

    assert len(result.detailed_summary) > 10

    assert result.related_issues is not None
    assert len(result.related_issues) > 0
