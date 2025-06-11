import os

import pytest
from fastmcp.tools import FunctionTool

from fastmcp_agents.agent.multi_step import MultiStepAgent
from fastmcp_agents.conversation.types import Conversation, SystemConversationEntry, UserConversationEntry
from fastmcp_agents.llm_link.litellm import LitellmLLMLink

MODEL = os.getenv("MODEL")

if not MODEL:
    msg = "MODEL environment variable is not set"
    raise ValueError(msg)


@pytest.fixture
def mock_tool():
    def mock_tool_fn():
        """A mock tool function."""
        return "test_tool_response"

    return FunctionTool.from_function(mock_tool_fn, name="test_tool", description="A test tool")


@pytest.fixture
def llm_link():
    return LitellmLLMLink(model="gpt-3.5-turbo")


@pytest.fixture
def agent(llm_link, mock_tool):
    return MultiStepAgent(
        name="test_agent", instructions="You are a test agent", description="A test agent", default_tools=[mock_tool], llm_link=llm_link
    )


def test_agent_initialization(agent):
    """Test that an agent can be initialized with the correct properties."""
    assert agent.name == "test_agent"
    assert agent.description == "A test agent"
    assert len(agent.default_tools) == 1
    assert agent.default_tools[0].name == "test_tool"
    assert agent.llm_link is not None


def test_agent_system_prompt_formatting():
    """Test that the system prompt is correctly formatted with agent details."""

    agent = MultiStepAgent(
        name="test_agent",
        description="Description: You have a description",
        instructions="Instructions: You have instructions",
        llm_link=LitellmLLMLink(),
    )

    # The system prompt should contain the agent name and description
    conversation = agent._prepare_conversation(conversation=None, task="Task: You have a task")
    assert isinstance(conversation, Conversation)
    assert len(conversation.entries) == 3

    assert isinstance(conversation.entries[0], SystemConversationEntry)
    assert "test_agent" in conversation.entries[0].content
    assert "You have a description" in conversation.entries[0].content

    assert isinstance(conversation.entries[1], UserConversationEntry)
    assert "You have instructions" in conversation.entries[1].content

    assert isinstance(conversation.entries[2], UserConversationEntry)
    assert "You have a task" in conversation.entries[2].content


def test_agent_with_custom_system_prompt():
    """Test that an agent can be initialized with a custom system prompt."""
    system_prompt = "System Prompt: You are a specialized test agent"
    instructions = "Instructions: You are a test agent"
    description = "Description: A test agent"
    agent = MultiStepAgent(
        name="test_agent",
        instructions=instructions,
        description=description,
        system_prompt=system_prompt,
        llm_link=LitellmLLMLink(),
    )

    conversation = agent._prepare_conversation(conversation=None, task="Custom Task")
    assert isinstance(conversation, Conversation)
    assert len(conversation.entries) == 3
    assert isinstance(conversation.entries[0], SystemConversationEntry)
    assert system_prompt in conversation.entries[0].content
    assert description not in conversation.entries[0].content

    assert isinstance(conversation.entries[1], UserConversationEntry)
    assert "Instructions: You are a test agent" in conversation.entries[1].content

    assert isinstance(conversation.entries[2], UserConversationEntry)
    assert "Custom Task" in conversation.entries[2].content


def test_agent_instantiation_step_limit():
    """Test that the agent respects the step limit."""
    agent = MultiStepAgent(
        name="test_agent", instructions="You are a test agent", description="A test agent", step_limit=5, llm_link=LitellmLLMLink()
    )

    assert agent.step_limit == 5
