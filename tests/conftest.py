import contextlib
import os
import tempfile
from collections.abc import AsyncGenerator, Callable, Coroutine, Sequence
from functools import wraps
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Client, FastMCP
from fastmcp.server.proxy import FastMCPProxy
from mcp.types import EmbeddedResource, ImageContent, TextContent

from fastmcp_agents.agent.extended.evaluator import EvaluationResult, EvaluatorAgent
from fastmcp_agents.agent.multi_step import MultiStepAgent
from fastmcp_agents.cli.loader import get_config_for_bundled
from fastmcp_agents.cli.models import AugmentedServerModel, ServerSettings
from fastmcp_agents.conversation.types import ToolConversationEntry
from fastmcp_agents.llm_link.litellm import LitellmLLMLink


class ReturnTrackingAsyncMock(AsyncMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_return_value_list = []

    async def _execute_mock_call(self, *args, **kwargs):
        value = await super()._execute_mock_call(*args, **kwargs)
        self.call_return_value_list.append(value)
        return value


@pytest.fixture
def server_config_name():
    """Override this fixture in test files to specify which config to use."""
    msg = "Override this fixture in test files to specify which config to use."
    raise NotImplementedError(msg)


@pytest.fixture
def server_settings():
    """Override this fixture in test files to specify server settings."""
    return ServerSettings(transport="stdio", log_level="DEBUG")


@pytest.fixture
def cli_server_config(server_config_name):
    """Get the server configuration based on the config name."""
    return get_config_for_bundled(server_config_name)


@pytest.fixture
async def compiled_configuration(
    cli_server_config: AugmentedServerModel, server_settings: ServerSettings
) -> AsyncGenerator[tuple[Sequence[MultiStepAgent], list[Client], FastMCP], None]:
    """Compile the server configuration with the given settings."""
    agents, mcp_clients, server = await cli_server_config.to_fastmcp_server(server_settings=server_settings)

    try:
        yield agents, mcp_clients, server
    finally:
        for client in mcp_clients:
            await client.close()


@pytest.fixture
def fastmcp_server(compiled_configuration: tuple[Sequence[MultiStepAgent], list[Client], FastMCP]) -> FastMCP:
    """Get the FastMCP server instance."""
    return compiled_configuration[2]


@pytest.fixture
def mcp_clients(compiled_configuration: tuple[Sequence[MultiStepAgent], list[Client], FastMCP]) -> list[Client]:
    """Get the list of MCP clients."""
    return compiled_configuration[1]


@pytest.fixture
def agents(compiled_configuration: tuple[Sequence[MultiStepAgent], list[Client], FastMCP]) -> Sequence[MultiStepAgent]:
    """Get the list of FastMCP agents."""
    return compiled_configuration[0]


@pytest.fixture
def agent_name():
    msg = "Override this fixture in test files to specify the name of the agent you are testing."
    raise NotImplementedError(msg)


@pytest.fixture
def agent(agent_name: str, agents: Sequence[MultiStepAgent]) -> MultiStepAgent:
    return next(agent for agent in agents if agent.name == agent_name)


@pytest.fixture
def agent_tool_calls(agent: MultiStepAgent) -> list[ToolConversationEntry]:
    assert isinstance(agent.call_tool, ReturnTrackingAsyncMock)

    return agent.call_tool.call_return_value_list


@pytest.fixture
def fastmcp_server_client(fastmcp_server: FastMCP) -> Client:
    """Create a client for the FastMCP server."""
    return Client(transport=fastmcp_server, timeout=120, init_timeout=30)


@pytest.fixture
async def initialized_client(fastmcp_server_client: Client) -> AsyncGenerator[Client, None]:
    """Initialize and yield a client, ensuring proper cleanup."""
    async with fastmcp_server_client:
        try:
            yield fastmcp_server_client
        finally:
            with contextlib.suppress(Exception):
                await fastmcp_server_client._disconnect()
                await fastmcp_server_client.close()


@pytest.fixture
def call_curator(
    initialized_client: Client,
) -> Callable[[str, str], Coroutine[Any, Any, list[TextContent | ImageContent | EmbeddedResource]]]:
    async def call_curator(name: str, task: str) -> list[TextContent | ImageContent | EmbeddedResource]:
        return await initialized_client.call_tool(name=name, arguments={"task": task})

    return call_curator


@pytest.fixture
def proxy_server(fastmcp_server_client: Client) -> FastMCPProxy:
    """Create a proxy server from the client."""
    return FastMCP.as_proxy(fastmcp_server_client)


@pytest.fixture
async def temp_working_dir() -> AsyncGenerator[Path, None]:
    original_dir = Path.cwd()

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)

        yield Path(temp_dir)

        os.chdir(original_dir)


@pytest.fixture
async def temp_dir() -> AsyncGenerator[Path, None]:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
async def evaluation_criteria() -> str | None:
    return None


def evaluate_with_criteria(criteria: str, minimum_grade: float = 0.9):
    """Decorator to evaluate test results against specified criteria.

    Args:
        criteria: The evaluation criteria to check against
        expected_grade: The expected grade (defaults to "A")
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Run the original test function
            agent, task, solution, conversation = await func(*args, **kwargs)

            # Create evaluator directly
            agent = EvaluatorAgent(
                name="evaluator",
                description="An agent that evaluates the result of a task.",
                instructions="You are a helpful assistant that evaluates the result of a task.",
                criteria=criteria,
                llm_link=LitellmLLMLink(),
            )

            # Run the evaluation
            evaluation = await agent.evaluate_result(ctx=MagicMock(), task=task, proposed_solution=solution, conversation=conversation)

            if not isinstance(evaluation, EvaluationResult):
                msg = f"Evaluation failed: {evaluation}"
                raise TypeError(msg)

            evaluation_grade: float = evaluation._grade()

            # Assert the grade matches expectations
            assert evaluation_grade >= minimum_grade, (
                f"Expected grade {minimum_grade}, got {evaluation_grade}. Feedback: {evaluation.feedback}"
            )

            return task, solution, evaluation

        return wrapper

    return decorator
