import json
from pathlib import Path

import pytest
from fastmcp import FastMCP
from fastmcp.tools import Tool as FastMCPTool

from fastmcp_agents.agent.fastmcp import FastMCPAgent
from fastmcp_agents.conversation.types import TextContent
from tests.conftest import evaluate_with_criteria


@pytest.fixture
def server_config_name():
    return "motherduckdb_mcp-server-motherduck"


class TestDuckDBAgent:
    @pytest.fixture
    def agent_name(self):
        return "ask_duckdb"

    @pytest.fixture
    async def populate_database(self, fastmcp_server: FastMCP):
        tools = await fastmcp_server.get_tools()

        query_tool: FastMCPTool = tools["query"]

        result = await query_tool.run(
            arguments={
                "query": """
            CREATE TABLE people (id INTEGER, name TEXT);
            INSERT INTO people (id, name) VALUES (1, 'John');
            INSERT INTO people (id, name) VALUES (2, 'Jane');
            INSERT INTO people (id, name) VALUES (3, 'Jim');
            INSERT INTO people (id, name) VALUES (4, 'Jill');
            INSERT INTO people (id, name) VALUES (5, 'Jack');
            """
            }
        )

        result = await query_tool.run(
            arguments={
                "query": """
            CREATE TABLE dogs (id INTEGER, name TEXT);
            INSERT INTO dogs (id, name) VALUES (1, 'Fido');
            INSERT INTO dogs (id, name) VALUES (2, 'Buddy');
            INSERT INTO dogs (id, name) VALUES (3, 'Max');
            INSERT INTO dogs (id, name) VALUES (4, 'Bella');
            INSERT INTO dogs (id, name) VALUES (5, 'Lucy');
            """
            }
        )

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the current tables were listed
        2. that the schema of each table was shown
        3. that a sample of data from each table was displayed
        4. that the agent used the correct sequence of tools
        5. that the agent did not run any unnecessary queries

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_database_inspection(
        self, temp_working_dir: Path, populate_database, agent: FastMCPAgent, call_curator, agent_tool_calls
    ):
        instructions = """
        Show me the current tables in the database, their schemas, and a sample of data from each table.
        """

        result = await call_curator(name=agent.name, instructions=instructions)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify database inspection was performed
        assert "table" in text_result.lower()
        assert "schema" in text_result.lower()
        assert "sample" in text_result.lower()

        # Verify tool calls
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]
        assert len(tool_call_names) > 4

        assert "tips_writing_queries" in tool_call_names
        assert "query" in tool_call_names

        return agent, instructions, text_result

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the JSON data was successfully loaded
        2. that the table was created with the correct schema
        3. that the data was properly imported
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_json_loading(self, temp_working_dir: Path, populate_database, agent: FastMCPAgent, call_curator, agent_tool_calls):
        instructions = """
        Load the JSON data from the file 'people.json' into a table called 'people'.
        Load the JSON data from the file 'dogs.json' into a table called 'dogs'.
        Show me the schema and a sample of the data from both tables.
        """

        result = await call_curator(name=agent.name, instructions=instructions)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify JSON was loaded
        assert "json" in text_result.lower()

        # Verify tool calls
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]
        assert len(tool_call_names) > 4
        assert "query" in tool_call_names
        assert "tips_load_json" in tool_call_names or "tips_load_json_file" in tool_call_names

        return agent, instructions, text_result

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the query was successfully executed
        2. that the results were properly formatted
        3. that the query logic was explained
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_query_execution(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        instructions = """
        Execute the following query and explain the results:
        SELECT * FROM my_data WHERE column1 > 100 ORDER BY column2 DESC LIMIT 5;
        """

        result = await call_curator(name=agent.name, instructions=instructions)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify query was executed
        assert "query" in text_result.lower()
        assert "results" in text_result.lower()
        assert "explanation" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 1
        assert agent_tool_calls[0].name == "get_query_tips"

        return agent, instructions, text_result

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation history must indicate:
        1. that the visualization was created
        2. that the data was properly formatted for visualization
        3. that the visualization type was appropriate
        4. that the agent used the correct sequence of tools

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_data_visualization(self, temp_working_dir: Path, agent: FastMCPAgent, call_curator, agent_tool_calls):
        instructions = """
        Create a visualization of the data in my_data table.
        Show the distribution of values in column1.
        """

        result = await call_curator(name=agent.name, instructions=instructions)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify visualization was created
        assert "visualization" in text_result.lower()
        assert "distribution" in text_result.lower()
        assert "column1" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 1
        assert agent_tool_calls[0].name == "get_query_tips"

        return agent, instructions, text_result
