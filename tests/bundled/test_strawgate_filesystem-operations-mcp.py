from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.agent.multi_step import DefaultSuccessResponseModel
from fastmcp_agents.conversation.utils import get_tool_calls_from_conversation
from tests.conftest import evaluate_with_criteria


@pytest.fixture
def server_config_name():
    return "strawgate_filesystem-operations-mcp"


class TestFilesystemOperationsAgent:
    @pytest.fixture
    def agent_name(self):
        return "ask_filesystem_operations_agent"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the file was successfully created
        2. that the content was written correctly
        3. that the file exists in the correct location
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_file_creation(self, temp_working_dir: Path, agent: CuratorAgent):
        task = """
        Create a new file called 'test.txt' in the current directory with the content 'Hello, World!'
        """

        conversation, task_success = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)

        # Verify file was created
        assert (temp_working_dir / "test.txt").exists()
        assert isinstance(task_success, DefaultSuccessResponseModel)
        assert "success" in task_success.result.lower()
        assert "created" in task_success.result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 1
        assert agent_tool_calls[0].name == "write_file"

        return agent, task, task_success, conversation

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the file was successfully read
        2. that the content was correctly retrieved
        3. that the file metadata was provided
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_file_reading(self, temp_working_dir: Path, agent: CuratorAgent):
        # First create a file to read
        (temp_working_dir / "test.txt").write_text("Hello, World!")

        task = """
        Read the contents of the file 'test.txt' and show me its metadata.
        """

        conversation, task_success = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)

        # Verify file was read
        assert isinstance(task_success, DefaultSuccessResponseModel)
        assert "hello, world!" in task_success.result.lower()
        assert "metadata" in task_success.result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 1
        assert agent_tool_calls[0].name == "read_file"

        return agent, task, task_success, conversation


class TestFilesystemSearchAgent:
    @pytest.fixture
    def agent_name(self):
        return "request_filesystem_search"

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the search was successfully performed
        2. that matching files were found
        3. that file metadata was provided
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_file_search(self, temp_working_dir: Path, agent: CuratorAgent):
        # First create some test files
        (temp_working_dir / "test1.txt").write_text("Hello, World!")
        (temp_working_dir / "test2.txt").write_text("Hello, Python!")
        (temp_working_dir / "other.txt").write_text("Different content")

        task = """
        Search for files containing the text 'Hello' in the current directory.
        Show me the file names and their contents.
        """

        conversation, task_success = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)

        # Verify search was performed
        assert isinstance(task_success, DefaultSuccessResponseModel)
        assert "test1.txt" in task_success.result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 1
        assert agent_tool_calls[0].name == "search_files"

        return agent, task, task_success, conversation

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the directory was successfully listed
        2. that file metadata was provided
        3. that the listing was properly formatted
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_directory_listing(self, temp_working_dir: Path, agent: CuratorAgent):
        # First create some test files
        (temp_working_dir / "test1.txt").write_text("Hello, World!")
        (temp_working_dir / "test2.txt").write_text("Hello, Python!")
        (temp_working_dir / "other.txt").write_text("Different content")

        task = """
        List all files in the current directory with their sizes and last modified dates.
        """

        conversation, task_success = await agent.perform_task_return_conversation(ctx=MagicMock(), task=task)

        agent_tool_calls = get_tool_calls_from_conversation(conversation)

        # Verify directory was listed
        assert isinstance(task_success, DefaultSuccessResponseModel)
        assert "test1.txt" in task_success.result.lower()
        assert "test2.txt" in task_success.result.lower()
        assert "other.txt" in task_success.result.lower()
        assert "size" in task_success.result.lower()
        assert "modified" in task_success.result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 1
        assert agent_tool_calls[0].name == "list_directory"

        return agent, task, task_success, conversation
