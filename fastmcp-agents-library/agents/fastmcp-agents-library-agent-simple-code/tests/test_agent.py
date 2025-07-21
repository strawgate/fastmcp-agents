import os
import shutil
from pathlib import Path

import pytest

from fastmcp_agents.library.agent.simple_code.implement import (
    CodeImplementationAgent,
    ImplementationResponse,
)
from fastmcp_agents.library.agent.simple_code.investigate import (
    CodeInvestigationAgent,
    InvestigationResponse,
)


def test_init():
    agent = CodeInvestigationAgent()
    assert agent is not None


@pytest.fixture
def playground_directory():
    playground_directory = Path(__file__).parent.parent / "playground"

    if playground_directory.exists():
        shutil.rmtree(playground_directory)
    playground_directory.mkdir(parents=True, exist_ok=True)

    # change the current working directory to the playground directory
    os.chdir(playground_directory)

    try:
        yield playground_directory
    finally:
        # change the current working directory back to the parent directory
        os.chdir(playground_directory.parent)


# @pytest.mark.asyncio
# async def test_investigating_code_agent(playground_directory: Path, server_client: Client[FastMCPTransport]):
#     agent = CodeInvestigationAgent()
#     assert agent is not None

#     async with server_client:
#         call_result = await server_client.call_tool(
#             name="ask_code_investigation_agent",
#             arguments={
#                 "task": "Create a new file called 'test.txt' in the playground directory",
#             }
#         )

#     assert isinstance(call_result, ToolResult)

#     assert call_result is not None

#     assert (playground_directory / "test.txt").exists()


@pytest.mark.asyncio
async def test_calculator_investigation(playground_directory: Path):
    agent = CodeInvestigationAgent()
    assert agent is not None

    result = await agent(
        git_url="https://github.com/strawgate/fastmcp-agents-tests-e2e.git",
        task="I can't figure out how to do matrix multiplication in the calculator. Please do a search for matrix.",
    )

    assert isinstance(result, InvestigationResponse)

    assert result is not None

    assert len(result.findings) > 0

    assert result.summary is not None

    context = agent._last_run_context
    assert context is not None

    tool_calls = context.tool_call_summary

    assert "read_file_lines" in tool_calls or "search_files" in tool_calls


@pytest.mark.asyncio
async def test_calculator_implementation(playground_directory: Path):
    agent = CodeImplementationAgent()
    assert agent is not None

    result = await agent(
        git_url="https://github.com/strawgate/fastmcp-agents-tests-e2e.git",
        task="Implement matrix multiplication in the calculator.",
    )

    assert isinstance(result, ImplementationResponse)

    assert result is not None

    assert result.summary is not None

    assert result.confidence is not None

    context = agent._last_run_context
    assert context is not None

    tool_calls = context.tool_call_summary

    assert "create_file" in tool_calls
    assert "read_file_lines" in tool_calls


@pytest.mark.asyncio
async def test_many_append_insert_replace(playground_directory: Path):
    agent = CodeImplementationAgent(step_limit=40)
    assert agent is not None

    result = await agent(
        git_url="https://github.com/strawgate/fastmcp-agents-tests-e2e.git",
        task="""Perform two appends, inserts, and replaces of lines in a file and verify the results. Upon completion, report failure
        if any of these operations did not work on the first try. If possible please try to explain why you think it did not work""",
    )

    assert isinstance(result, ImplementationResponse)

    assert result is not None

    assert result.summary is not None

    assert result.confidence is not None

    context = agent._last_run_context
    assert context is not None

    tool_calls = context.tool_call_summary

    assert "create_file" in tool_calls
    assert "read_file_lines" in tool_calls


@pytest.mark.asyncio
async def test_many_filesystem_operations(playground_directory: Path):  # pyright: ignore[reportUnusedParameter]
    agent = CodeImplementationAgent(step_limit=40)
    assert agent is not None

    result = await agent(
        git_url="https://github.com/strawgate/fastmcp-agents-tests-e2e.git",
        task="""Perform two of each type of filesystem operation and verify the results. Upon completion, report failure
        if any of these operations did not work on the first try. If possible please try to explain why you think it did not work""",
    )

    assert isinstance(result, ImplementationResponse)

    assert result is not None

    assert result.summary is not None

    assert result.confidence is not None

    context = agent._last_run_context
    assert context is not None

    tool_calls = context.tool_call_summary

    assert "create_file" in tool_calls
    assert "read_file_lines" in tool_calls
