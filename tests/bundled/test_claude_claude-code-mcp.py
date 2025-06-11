from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.conversation.utils import get_tool_calls_from_conversation
from tests.conftest import evaluate_with_criteria


@pytest.fixture
def server_config_name():
    return "claude_claude-code-mcp"


@pytest.fixture
def project_in_dir(temp_working_dir: Path):
    # Create a simple Python project for testing
    project_dir = temp_working_dir / "test_project"
    project_dir.mkdir()

    # Create a simple Python file
    (project_dir / "main.py").write_text("""
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
    """)

    # Create a test file
    (project_dir / "test_main.py").write_text("""
def test_hello_world():
    from main import hello_world
    # This is a placeholder test
    assert True
    """)

    return project_dir


class TestClaudeCodeAgent:
    @pytest.fixture
    def agent_name(self):
        return "ask_claude_code_agent"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the project was successfully analyzed
        2. that the code structure was understood
        3. that the agent provided meaningful insights about the code
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_code_analysis(self, project_in_dir: Path, agent: CuratorAgent):
        task = """
        1. Analyze the code in the test_project directory
        2. Explain the structure and functionality of the code
        3. Identify any potential improvements
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        # Verify that appropriate tools were called
        assert "Task" in tool_call_names

        return agent, task, result, conversation

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the test file was successfully modified
        2. that the test was properly implemented
        3. that the changes were appropriate for the code being tested
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_code_modification(self, project_in_dir: Path, agent: CuratorAgent):
        task = """
        1. Improve the test in test_main.py to properly test the hello_world function
        2. Add appropriate assertions
        3. Make sure the test is well documented
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        # Verify that appropriate tools were called
        assert "Task" in tool_call_names

        return agent, task, result, conversation
