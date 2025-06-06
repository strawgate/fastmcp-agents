import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastmcp import FastMCP

from fastmcp_agents.agent.fastmcp import FastMCPAgent
from fastmcp_agents.conversation.types import TextContent
from tests.conftest import evaluate_with_criteria

if TYPE_CHECKING:
    from fastmcp.tools import Tool as FastMCPTool


@pytest.fixture
def server_config_name():
    return "motherduckdb_mcp-server-motherduck"


class TestDuckDBAgent:
    @pytest.fixture
    def agent_name(self):
        return "ask_duckdb_agent"

    @pytest.fixture
    async def populate_database(self, fastmcp_server: FastMCP):
        tools = await fastmcp_server.get_tools()

        query_tool: FastMCPTool = tools["query"]

        await query_tool.run(
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

        await query_tool.run(
            arguments={
                "query": """
            CREATE TABLE dogs (id INTEGER, name TEXT, age INTEGER, color TEXT, sibling_ages INTEGER[]);
            INSERT INTO dogs (id, name, age, color, sibling_ages) VALUES (1, 'Fido', 100, 'red', [1, 2, 3]);
            INSERT INTO dogs (id, name, age, color, sibling_ages) VALUES (2, 'Buddy', 200, 'blue', [3, 4, 8]);
            INSERT INTO dogs (id, name, age, color, sibling_ages) VALUES (3, 'Max', 300, 'green', [7, 8, 9]);
            INSERT INTO dogs (id, name, age, color, sibling_ages) VALUES (4, 'Bella', 400, 'purple', [9, 10, 11]);
            INSERT INTO dogs (id, name, age, color, sibling_ages) VALUES (5, 'Lucy', 500, 'yellow', [13, 1, 15]);
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
        task = """
        Show me the current tables in the database, their schemas, and a sample of data from each table.
        """

        result = await call_curator(name=agent.name, task=task)

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

        assert "tips_using_query_tool" in tool_call_names
        assert "query" in tool_call_names

        return agent, task, text_result

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
    async def test_json_loading(self, temp_working_dir: Path, agent: FastMCPAgent, fastmcp_server: FastMCP, call_curator, agent_tool_calls):
        task = """
        Load the JSON data from the file 'people.json' into a table called 'people'.
        Load the JSON data from the file 'dogs.json' into a table called 'dogs'.
        Show me the schema and a sample of the data from both tables.
        """

        # Create a temporary file with JSON data
        people_json = [
            {"id": 1, "name": "Tom"},
            {"id": 2, "name": "Dick"},
            {"id": 3, "name": "Harry"},
        ]
        dogs_json = [
            {"id": 1, "name": "Fido", "age": 100, "color": "red", "sibling_ages": [1, 2, 3]},
            {"id": 2, "name": "Buddy", "age": 200, "color": "blue", "sibling_ages": [3, 4, 8]},
            {"id": 3, "name": "Kepler", "age": 300, "color": "green", "sibling_ages": [7, 8, 9]},
            {"id": 4, "name": "Bella", "age": 400, "color": "purple", "sibling_ages": [9, 10, 11]},
            {"id": 5, "name": "Lucy", "age": 500, "color": "yellow", "sibling_ages": [13, 1, 15]},
        ]

        with Path("people.json").open("w", encoding="utf-8") as f:
            json.dump(people_json, f)
        with Path("dogs.json").open("w", encoding="utf-8") as f:
            json.dump(dogs_json, f)

        result = await call_curator(name=agent.name, task=task)

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

        return agent, task, text_result

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
    async def test_query_execution(
        self, temp_working_dir: Path, populate_database, agent: FastMCPAgent, fastmcp_server: FastMCP, call_curator, agent_tool_calls
    ):
        task = """
        Execute the following query and explain the results:
        SELECT * FROM my_data WHERE age > 100 ORDER BY birthyear DESC LIMIT 5;
        """
        tools = await fastmcp_server.get_tools()

        query_tool: FastMCPTool = tools["query"]

        result = await query_tool.run(
            arguments={
                "query": """
            CREATE TABLE my_data (id INTEGER, name TEXT, birthyear INTEGER, age INTEGER, color TEXT, sibling_ages INTEGER[]);
            INSERT INTO my_data (id, name, birthyear, age, color, sibling_ages) VALUES (1, 'Fido', 1900, 100, 'red', [1, 2, 3]);
            INSERT INTO my_data (id, name, birthyear, age, color, sibling_ages) VALUES (2, 'Buddy', 1800, 200, 'blue', [4, 5, 6]);
            INSERT INTO my_data (id, name, birthyear, age, color, sibling_ages) VALUES (3, 'Max', 1700, 300, 'green', [7, 8, 9]);
            INSERT INTO my_data (id, name, birthyear, age, color, sibling_ages) VALUES (4, 'Bella', 1600, 400, 'purple', [10, 11, 12]);
            INSERT INTO my_data (id, name, birthyear, age, color, sibling_ages) VALUES (5, 'Lucy', 1500, 500, 'yellow', [13, 14, 15]);
            """
            }
        )
        result = await call_curator(name=agent.name, task=task)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify query was executed
        assert "query" in text_result.lower()
        assert "results" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 1
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]

        assert "query" in tool_call_names

        return agent, task, text_result

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
    async def test_data_visualization(self, temp_working_dir: Path, populate_database, agent: FastMCPAgent, call_curator, agent_tool_calls):
        task = """
        Create an ascii visualization of the data in dogs table.
        Show the distribution of values in sibling ages.
        """

        result = await call_curator(name=agent.name, task=task)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Verify visualization was created
        assert "distribution" in text_result.lower()
        assert "age" in text_result.lower()

        # Verify tool calls
        assert len(agent_tool_calls) >= 1
        tool_call_names = [tool_call.name for tool_call in agent_tool_calls]
        assert "tips_using_query_tool" in tool_call_names
        assert "query" in tool_call_names

        return agent, task, text_result
