import os

import pytest
from mcp.types import Tool

from fastmcp_agents.agent.basic import FastMCPAgent
from fastmcp_agents.llm_link.lltellm import AsyncLitellmLLMLink

MODEL = os.getenv("MODEL")

if not MODEL:
    msg = "MODEL environment variable is not set"
    raise ValueError(msg)


@pytest.fixture
def mock_tool():
    return Tool(
        name="test_tool",
        description="A test tool",
        inputSchema={
            "type": "object",
            "properties": {"test_param": {"type": "string", "description": "A test parameter"}},
            "required": ["test_param"],
        },
    )


@pytest.fixture
def llm_link():
    return AsyncLitellmLLMLink(model="gpt-3.5-turbo")


@pytest.fixture
def agent(llm_link, mock_tool):
    return FastMCPAgent(name="test_agent", description="A test agent", default_tools=[mock_tool], llm_link=llm_link)


def test_agent_initialization(agent):
    """Test that an agent can be initialized with the correct properties."""
    assert agent.name == "test_agent"
    assert agent.description == "A test agent"
    assert len(agent.default_tools) == 1
    assert agent.default_tools[0].name == "test_tool"
    assert agent.llm_link is not None


def test_agent_system_prompt_formatting():
    """Test that the system prompt is correctly formatted with agent details."""
    agent = FastMCPAgent(name="test_agent", description="A test agent that can do things", llm_link=AsyncLitellmLLMLink())

    # The system prompt should contain the agent name and description
    system_prompt = agent.get_system_prompt()
    assert "test_agent" in system_prompt.entries[0].content
    assert "A test agent that can do things" in system_prompt.entries[0].content


def test_agent_with_custom_system_prompt():
    """Test that an agent can be initialized with a custom system prompt."""
    custom_prompt = "You are a specialized test agent"
    agent = FastMCPAgent(name="test_agent", description="A test agent", system_prompt=custom_prompt, llm_link=AsyncLitellmLLMLink())

    system_prompt = agent.get_system_prompt()
    assert system_prompt.entries[0].content == custom_prompt


def test_agent_instantiation_step_limit():
    """Test that the agent respects the step limit."""
    agent = FastMCPAgent(name="test_agent", description="A test agent", step_limit=5, llm_link=AsyncLitellmLLMLink())

    assert agent.step_limit == 5


def test_agent_instantiation_max_parallel_tool_calls():
    """Test that the agent respects the max parallel tool calls limit."""
    agent = FastMCPAgent(name="test_agent", description="A test agent", max_parallel_tool_calls=3, llm_link=AsyncLitellmLLMLink())

    assert agent.max_parallel_tool_calls == 3
