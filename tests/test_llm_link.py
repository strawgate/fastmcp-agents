import os

import pytest
from fastmcp.tools import FunctionTool
from mcp.types import Tool

from fastmcp_agents.conversation.types import Conversation, SystemConversationEntry, UserConversationEntry
from fastmcp_agents.errors.llm_link import ModelDoesNotSupportFunctionCallingError
from fastmcp_agents.llm_link.litellm import LiteLLMCompletionSettings, LitellmLLMLink, LiteLLMSettings


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
        LitellmLLMLink(model="invalid-model")


def test_litellm_settings_model_required():
    """Test that Litellm settings are correctly initialized."""
    del os.environ["MODEL"]

    with pytest.raises(expected_exception=ValueError, match="Model is required for Litellm"):
        LiteLLMSettings()


def test_litellm_settings_from_env():
    os.environ["MODEL"] = "gpt-4o"
    os.environ["TEMPERATURE"] = "0.5"
    os.environ["REASONING_EFFORT"] = "low"
    os.environ["PRESENCE_PENALTY"] = "0.0"

    settings = LiteLLMSettings()
    assert settings.model == "gpt-4o"
    assert settings.temperature == 0.5
    assert settings.reasoning_effort == "low"
    assert settings.presence_penalty == 0.0


def test_litellm_completion_settings_from_env():
    os.environ["LITELLM_COMPLETION_KWARGS_KEY"] = "value"
    settings = LiteLLMCompletionSettings()
    assert settings.kwargs == {"key": "value"}
