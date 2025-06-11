import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.conversation.utils import get_tool_calls_from_conversation
from tests.conftest import evaluate_with_criteria


@pytest.fixture
def server_config_name():
    return "flow_code-agent"


@pytest.fixture
def project_in_dir(temp_working_dir: Path):
    # Create a simple Python project for testing
    project_dir = temp_working_dir / "test_project"
    project_dir.mkdir()

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=project_dir, check=True)

    # Create a simple Python file with a bug
    (project_dir / "calculator.py").write_text("""
def add(a, b):
    return a - b  # Bug: should be addition

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
    """)

    # Create a test file
    (project_dir / "test_calculator.py").write_text("""
def test_add():
    from calculator import add
    assert add(2, 3) == 5  # This will fail due to the bug

def test_subtract():
    from calculator import subtract
    assert subtract(5, 3) == 2

def test_multiply():
    from calculator import multiply
    assert multiply(2, 3) == 6

def test_divide():
    from calculator import divide
    assert divide(6, 2) == 3
    """)

    # Add and commit the files
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit with calculator implementation"], cwd=project_dir, check=True)

    return project_dir


class TestCodeAgent:
    @pytest.fixture
    def agent_name(self):
        return "ask_code_agent"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the task was properly analyzed
        2. that a plan was created
        3. that the plan was executed
        """,
        minimum_grade=0.9,
    )
    async def test_analyze_repo(self, project_in_dir: Path, agent: CuratorAgent):
        task = """
        1. Analyze the code in the repository
        2. Explain the structure and functionality of the code
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        # Verify that appropriate tools were called
        potential_calls = ["ask_filesystem_operations_agent", "ask_tree_sitter_agent", "get_structure", "git"]
        assert any(call in tool_call_names for call in potential_calls)

        return agent, task, result, conversation

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the bug was properly identified
        2. that a test was written to demonstrate the bug
        3. that the bug was fixed
        5. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_bug_fix(self, project_in_dir: Path, agent: CuratorAgent):
        task = """
        1. Analyze the calculator.py file
        2. Identify and fix the bug in the add function
        3. Ensure there is a test that verifies the bug is fixed
        4. Fix the bug
        5. Verify the fix works
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        # Verify that appropriate tools were called
        potential_calls = ["get_structure", "ask_filesystem_operations_agent", "ask_tree_sitter_agent"]
        assert any(call in tool_call_names for call in potential_calls)

        return agent, task, result, conversation

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the code was properly analyzed
        2. that a refactoring plan was created
        3. that the refactoring was implemented
        4. that the functionality was preserved
        5. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_code_refactoring(self, project_in_dir: Path, agent: CuratorAgent):
        task = """
        1. Analyze the calculator.py file
        2. Create a plan to refactor the code to use a Calculator class
        3. Implement the refactoring
        4. Update the tests to work with the new class-based implementation
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        # Verify that appropriate tools were called
        potential_calls = ["register_project_tool", "get_structure", "ask_filesystem_operations_agent", "ask_tree_sitter_agent"]
        assert any(call in tool_call_names for call in potential_calls)

        return agent, task, result, conversation

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the requirements were properly analyzed
        2. that an implementation plan was created
        3. that the new feature was implemented
        4. that appropriate tests were written
        5. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_feature_implementation(self, project_in_dir: Path, agent: CuratorAgent):
        task = """
        1. Analyze the calculator.py file
        2. Create a plan to add a new 'power' function that raises a number to a given exponent
        3. Implement the new function
        4. Write tests for the new function
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        # Verify that appropriate tools were called
        potential_calls = ["create_file", "get_structure", "ask_filesystem_operations_agent", "ask_tree_sitter_agent"]
        assert any(call in tool_call_names for call in potential_calls)

        return agent, task, result, conversation

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the problem was properly analyzed
        2. that a solution plan was created
        3. that the solution was implemented
        4. that the solution is correct
        5. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_problem_solution(self, project_in_dir: Path, agent: CuratorAgent):
        task = """
        1. Analyze the calculator.py file
        2. Create a plan to handle decimal precision issues in the divide function
        3. Implement a solution that ensures consistent decimal precision
        4. Write tests to verify the precision handling
        """

        conversation, result = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        # Verify that appropriate tools were called
        potential_calls = ["create_file", "get_structure", "ask_filesystem_operations_agent", "ask_tree_sitter_agent"]
        assert any(call in tool_call_names for call in potential_calls)

        return agent, task, result, conversation
