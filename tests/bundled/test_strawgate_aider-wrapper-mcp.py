import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.agent.multi_step import DefaultSuccessResponseModel
from fastmcp_agents.conversation.utils import get_tool_calls_from_conversation
from tests.conftest import evaluate_with_criteria


@pytest.fixture
def server_config_name():
    return "strawgate_aider-wrapper-mcp"


@pytest.fixture
def project_in_dir(temp_working_dir: Path):
    # Create a simple Python project for testing
    project_dir = temp_working_dir / "test_project"
    project_dir.mkdir()

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=project_dir, check=True)

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

    # Add and commit the files
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, check=True)

    return project_dir


class TestAiderAgent:
    @pytest.fixture
    def agent_name(self):
        return "ask_aider_agent"

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
        1. Set the repo to the test_project directory
        2. Analyze the code in the test_project directory
        3. Explain the structure and functionality of the code
        4. Identify any potential improvements
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        # Verify that appropriate tools were called
        assert "set_repo" in tool_call_names
        assert "get_code_structure" in tool_call_names
        assert "get_structured_repo_map" in tool_call_names

        return agent, task, result, conversation

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the test file was successfully modified
        2. that the test was properly implemented
        3. that the changes were appropriate for the code being tested
        4. that the agent used the correct sequence of tools
        5. that the changes were properly committed to git

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_code_modification(self, project_in_dir: Path, agent: CuratorAgent):
        task = """
        1. Set the repo to the test_project directory
        2. Improve the test in test_main.py to properly test the hello_world function
        3. Add appropriate assertions
        4. Make sure the test is well documented
        5. Commit the changes with a descriptive message
        """

        conversation, task_success = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        # Verify that appropriate tools were called
        assert isinstance(task_success, DefaultSuccessResponseModel)
        assert any("set_repo" in name.lower() for name in tool_call_names)
        assert any("write_code" in name.lower() for name in tool_call_names)

        return agent, task, task_success, conversation
