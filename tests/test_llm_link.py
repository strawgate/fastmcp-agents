import os

import pytest
from fastmcp.tools import FunctionTool
from mcp.types import Tool

from fastmcp_agents.conversation.types import Conversation, SystemConversationEntry, UserConversationEntry
from fastmcp_agents.errors.llm_link import ModelDoesNotSupportFunctionCallingError
from fastmcp_agents.llm_link.litellm import AsyncLitellmLLMLink


@pytest.fixture
def mock_mcp_tool():
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
def mock_fastmcp_tool():
    def test_tool():
        pass

    return FunctionTool.from_function(fn=test_tool)


@pytest.fixture
def conversation():
    conv = Conversation()
    conv = conv.append(SystemConversationEntry(content="You are a test assistant"))
    return conv.append(UserConversationEntry(content="Test message"))


def test_llm_link_initialization_with_invalid_model():
    """Test that LLM link initialization fails with an invalid model."""
    with pytest.raises(ModelDoesNotSupportFunctionCallingError):
        AsyncLitellmLLMLink(model="invalid-model")


async def test_llm_link_completion_with_tools(mock_fastmcp_tool, conversation):
    """Test that LLM link can make a completion with tools."""
    # Use a real model that supports function calling
    model = os.getenv("MODEL", "gpt-3.5-turbo")
    llm_link = AsyncLitellmLLMLink(model=model)

    assistant_conversation_entry = await llm_link.async_completion(conversation=conversation, fastmcp_tools=[mock_fastmcp_tool])

    tool_calls = assistant_conversation_entry.tool_calls
    # Verify tool calls were generated
    assert isinstance(tool_calls, list)
    if tool_calls:  # Some models might not always generate tool calls
        assert all(hasattr(call, "name") for call in tool_calls)
        assert all(hasattr(call, "arguments") for call in tool_calls)
