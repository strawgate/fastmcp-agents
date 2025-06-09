import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.conversation.utils import get_tool_calls_from_conversation
from tests.conftest import evaluate_with_criteria


@pytest.fixture
def server_config_name():
    return "wrale_mcp-server-tree-sitter"


@pytest.fixture
def project_in_dir(temp_working_dir: Path):
    # git clone the tree-sitter-server repo
    subprocess.run(["git", "clone", "https://github.com/wrale/mcp-server-tree-sitter.git", temp_working_dir / "test_project"], check=False)
    return temp_working_dir / "test_project"


class TestTreeSitterAgent:
    @pytest.fixture
    def agent_name(self):
        return "ask_tree_sitter_agent"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the project was successfully registered
        2. that the project was analyzed
        3. that the agent used the correct sequence of tools
        4. that the agent did not call any unnecessary tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_project_registration(self, project_in_dir: Path, agent: CuratorAgent):
        task = """
        1. Register the project in the test_project directory
        2. Produce a basic analysis/query of the project
        """

        conversation, task_success = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        assert "register_project_tool" in tool_call_names
        assert "analyze_project" in tool_call_names

        return agent, task, task_success, conversation

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the project was successfully registered
        2. that the search for the specified text was performed
        3. that the results were properly formatted and returned
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_text_search(self, project_in_dir: Path, agent: CuratorAgent):
        task = """
        1. Register the project in the test_project directory
        2. Search for the text 'def test_' in all files
        3. Return the results in a clear format
        """

        conversation, task_success = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        assert "register_project_tool" in tool_call_names
        assert "find_text" in tool_call_names

        return agent, task, task_success, conversation

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the project was successfully registered
        2. that the symbol search was performed
        3. that the results were properly formatted and returned
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_symbol_search(self, project_in_dir: Path, agent: CuratorAgent):
        task = """
        1. Register the project in the test_project directory
        2. Analyze the project and find all function definitions in the project
        3. Return the results in a clear format
        """

        conversation, task_success = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        assert "register_project_tool" in tool_call_names
        assert "analyze_project" in tool_call_names
        assert "run_query" in tool_call_names

        return agent, task, task_success, conversation
