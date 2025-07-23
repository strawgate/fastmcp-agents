import os
import shutil
from pathlib import Path

import pytest
from pydantic import AnyHttpUrl

from fastmcp_agents.library.agent.simple_code.implement import (
    ImplementationResponse,
    code_implementation_agent,
    implement_code,
)
from fastmcp_agents.library.agent.simple_code.investigate import (
    InvestigationResponse,
    code_investigation_agent,
    investigate_code,
)


def test_init_agents():
    assert code_investigation_agent is not None
    assert code_implementation_agent is not None


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
    investigation_reponse: InvestigationResponse = await investigate_code(
        code_repository=AnyHttpUrl("https://github.com/strawgate/fastmcp-agents-tests-e2e.git"),
        task="I can't figure out how to do matrix multiplication in the calculator. Please do a search for matrix.",
    )

    assert isinstance(investigation_reponse, InvestigationResponse)

    assert investigation_reponse is not None

    assert len(investigation_reponse.findings) > 0

    assert investigation_reponse.summary is not None


@pytest.mark.asyncio
async def test_calculator_implementation(playground_directory: Path):
    implementation_response: ImplementationResponse = await implement_code(
        code_repository=AnyHttpUrl("https://github.com/strawgate/fastmcp-agents-tests-e2e.git"),
        task="Implement matrix multiplication in the calculator.",
    )

    assert isinstance(implementation_response, ImplementationResponse)

    assert implementation_response.confidence is not None

    assert implementation_response.summary is not None

    assert implementation_response.potential_flaws is not None


@pytest.mark.asyncio
async def test_many_append_insert_replace(playground_directory: Path):
    implementation_response: ImplementationResponse = await implement_code(
        code_repository=AnyHttpUrl("https://github.com/strawgate/fastmcp-agents-tests-e2e.git"),
        task="""Perform two appends, inserts, and replaces of lines in a file and verify the results. Upon completion, report failure
        if any of these operations did not work on the first try. If possible please try to explain why you think it did not work""",
    )

    assert isinstance(implementation_response, ImplementationResponse)

    assert implementation_response is not None

    assert implementation_response.summary is not None

    assert implementation_response.confidence is not None

    assert implementation_response.potential_flaws is not None
