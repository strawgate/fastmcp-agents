from pathlib import Path

import pytest

from fastmcp_agents.agent.fastmcp import FastMCPAgent
from fastmcp_agents.conversation.types import TextContent
from tests.conftest import evaluate_with_criteria


@pytest.fixture
def server_config_name():
    return "strawgate_filesystem-operations"


class TestFilesystemOperationsAgent:
    @pytest.fixture
    def agent_name(self):
        return "request_filesystem_operations"

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
    async def test_file_creation(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        task = """
        Create a new file called 'test.txt' in the current directory with the content 'Hello, World!'
        """

        result = await call_curator(name=agent.name, task=task)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify file was created
        assert (temp_working_dir / "test.txt").exists()
        assert "success" in text_result.lower()
        assert "created" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 1
        assert agent_tool_calls[0].name == "write_file"

        return agent, task, text_result

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
    async def test_file_reading(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        # First create a file to read
        (temp_working_dir / "test.txt").write_text("Hello, World!")

        task = """
        Read the contents of the file 'test.txt' and show me its metadata.
        """

        result = await call_curator(name=agent.name, task=task)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify file was read
        assert "hello, world!" in text_result.lower()
        assert "metadata" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 1
        assert agent_tool_calls[0].name == "read_file"

        return agent, task, text_result


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
    async def test_file_search(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        # First create some test files
        (temp_working_dir / "test1.txt").write_text("Hello, World!")
        (temp_working_dir / "test2.txt").write_text("Hello, Python!")
        (temp_working_dir / "other.txt").write_text("Different content")

        task = """
        Search for files containing the text 'Hello' in the current directory.
        Show me the file names and their contents.
        """

        result = await call_curator(name=agent.name, task=task)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify search was performed
        assert "test1.txt" in text_result.lower()
        assert "test2.txt" in text_result.lower()
        assert "hello" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 1
        assert agent_tool_calls[0].name == "search_files"

        return agent, task, text_result

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
    async def test_directory_listing(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        # First create some test files
        (temp_working_dir / "test1.txt").write_text("Hello, World!")
        (temp_working_dir / "test2.txt").write_text("Hello, Python!")
        (temp_working_dir / "other.txt").write_text("Different content")

        task = """
        List all files in the current directory with their sizes and last modified dates.
        """

        result = await call_curator(name=agent.name, task=task)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify directory was listed
        assert "test1.txt" in text_result.lower()
        assert "test2.txt" in text_result.lower()
        assert "other.txt" in text_result.lower()
        assert "size" in text_result.lower()
        assert "modified" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 1
        assert agent_tool_calls[0].name == "list_directory"

        return agent, task, text_result
