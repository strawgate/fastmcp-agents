from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from fastmcp_agents.agent.basic import FastMCPAgent
from fastmcp_agents.conversation.types import TextContent
from tests.conftest import ReturnTrackingAsyncMock, evaluate_with_criteria


@pytest.fixture
def server_config_name():
    return "cyanheads_git-mcp-server"


class TestGitAgent:

    @pytest.fixture
    def git_agent(self, agents: list[FastMCPAgent]):
        agent = next(agent for agent in agents if agent.name == "git_agent")
        agent.run = ReturnTrackingAsyncMock(wraps=agent.run)
        return agent

    @evaluate_with_criteria(
        criteria="""
        The result and the conversation historymust indicate:
        1. that the repository was successfully cloned
        2. that it has been cloned to a path that is appropriate for the task
        3. 

        Any other response is a failure.
        """,
        minimum_grade=0.9,
    )
    async def test_ask_git_for_clone(self, temp_working_dir: Path, git_agent: FastMCPAgent, call_curator):
        instructions = "Clone the repository https://github.com/modelcontextprotocol/servers"

        result = await call_curator(name=git_agent.name, instructions=instructions)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_result = result[0].text

        # Check if there is now a servers directory
        assert (temp_working_dir / "servers").exists()

        # Ensure it has a README.md file
        assert (temp_working_dir / "servers" / "README.md").exists()

        assert "success" in text_result.lower()
        assert "servers" in text_result.lower()

        return git_agent, instructions, text_result
