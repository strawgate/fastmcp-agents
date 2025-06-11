from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.agent.multi_step import DefaultSuccessResponseModel
from fastmcp_agents.conversation.utils import get_tool_calls_from_conversation
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
    async def test_issue_summarization(self, temp_working_dir: Path, agent: CuratorAgent):
        task = """
        Summarize issue #1 in the repository modelcontextprotocol/servers.
        Include any relevant comments and provide a clear overview of the issue's status and content.
        """

        conversation, task_success = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)

        # Verify issue was retrieved and summarized
        assert isinstance(task_success, DefaultSuccessResponseModel)
        assert "issue" in task_success.result.lower()
        assert "slack" in task_success.result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 2
        assert agent_tool_calls[0].name == "get_issue"
        assert agent_tool_calls[1].name == "get_issue_comments"

        return agent, task, task_success, conversation

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
    async def test_related_issues(self, temp_working_dir: Path, agent: CuratorAgent):
        task = """
        Find issues related to issue #1 in the repository modelcontextprotocol/servers.
        Include a confidence rating for each related issue and explain why it's related.
        """

        conversation, task_success = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)

        # Verify related issues were found
        assert isinstance(task_success, DefaultSuccessResponseModel)
        assert "related" in task_success.result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 2
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]
        assert "get_issue" in tool_call_names
        assert "search_issues" in tool_call_names

        return agent, task, task_success, conversation


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
    async def test_pr_summarization(self, temp_working_dir: Path, agent: CuratorAgent):
        task = """
        Summarize pull request #1 in the repository modelcontextprotocol/servers.
        Include the files changed, review status, and any relevant comments.
        """

        conversation, task_success = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)

        # Verify PR was retrieved and summarized
        assert isinstance(task_success, DefaultSuccessResponseModel)
        assert "pull request" in task_success.result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 4
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]
        assert "get_pull_request" in tool_call_names
        assert "get_pull_request_files" in tool_call_names
        assert "get_pull_request_comments" in tool_call_names

        return agent, task, task_success, conversation

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
    async def test_pr_reviews(self, temp_working_dir: Path, agent: CuratorAgent):
        task = """
        Summarize the review status of pull request #1 in the repository modelcontextprotocol/servers.
        Include the review status, reviewer comments, and any requested changes.
        """

        conversation, task_success = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)

        # Verify reviews were retrieved and summarized
        assert isinstance(task_success, DefaultSuccessResponseModel)
        assert "review" in task_success.result.lower()
        assert "status" in task_success.result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 2
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]
        assert "get_pull_request_comments" in tool_call_names
        assert "get_pull_request_reviews" in tool_call_names

        return agent, task, task_success, conversation
