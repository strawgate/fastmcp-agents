from pathlib import Path

import pytest

from fastmcp_agents.agent.fastmcp import FastMCPAgent
from fastmcp_agents.conversation.types import TextContent
from tests.conftest import evaluate_with_criteria


@pytest.fixture
def server_config_name():
    return "github_github-mcp-server"


class TestGitHubAgent:
    @pytest.fixture
    def agent_name(self):
        return "summarize_github_issue"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the issue was successfully retrieved
        2. that the issue comments were retrieved
        3. that a clear summary of the issue and comments was provided
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_issue_summarization(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        task = """
        Summarize issue #1 in the repository modelcontextprotocol/servers.
        Include any relevant comments and provide a clear overview of the issue's status and content.
        """

        result = await call_curator(name=agent.name, task=task)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify issue was retrieved and summarized
        assert "issue" in text_result.lower()
        assert "summary" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 2
        assert agent_tool_calls[0].name == "get_issue"
        assert agent_tool_calls[1].name == "get_issue_comments"

        return agent, task, text_result

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the issue was successfully retrieved
        2. that related issues were searched for
        3. that a clear summary of related issues was provided
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_related_issues(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        task = """
        Find issues related to issue #1 in the repository modelcontextprotocol/servers.
        Include a confidence rating for each related issue and explain why it's related.
        """

        result = await call_curator(name=agent.name, task=task)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify related issues were found
        assert "related" in text_result.lower()
        assert "confidence" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 2
        assert agent_tool_calls[0].name == "get_issue"
        assert agent_tool_calls[1].name == "search_issues"

        return agent, task, text_result


class TestPullRequestAgent:
    @pytest.fixture
    def agent_name(self):
        return "summarize_pull_request"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the pull request was successfully retrieved
        2. that the PR files were retrieved
        3. that the PR status was checked
        4. that a clear summary of the PR was provided
        5. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_pr_summarization(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        task = """
        Summarize pull request #1 in the repository modelcontextprotocol/servers.
        Include the files changed, review status, and any relevant comments.
        """

        result = await call_curator(name=agent.name, task=task)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify PR was retrieved and summarized
        assert "pull request" in text_result.lower()
        assert "summary" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 4
        assert agent_tool_calls[0].name == "get_pull_request"
        assert agent_tool_calls[1].name == "get_pull_request_files"
        assert agent_tool_calls[2].name == "get_pull_request_status"
        assert agent_tool_calls[3].name == "get_pull_request_comments"

        return agent, task, text_result

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the pull request was successfully retrieved
        2. that the PR reviews were retrieved
        3. that a clear summary of the review status was provided
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_pr_reviews(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        task = """
        Summarize the review status of pull request #1 in the repository modelcontextprotocol/servers.
        Include the review status, reviewer comments, and any requested changes.
        """

        result = await call_curator(name=agent.name, task=task)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify reviews were retrieved and summarized
        assert "review" in text_result.lower()
        assert "status" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 2
        assert agent_tool_calls[0].name == "get_pull_request"
        assert agent_tool_calls[1].name == "get_pull_request_reviews"

        return agent, task, text_result
