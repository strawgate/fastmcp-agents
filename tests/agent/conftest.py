import pytest
from fastmcp.tools import FunctionTool

from fastmcp_agents.llm_link.litellm import LitellmLLMLink


@pytest.fixture(name="tool")
def mock_tool():
    def mock_tool_fn():
        """A mock tool function."""
        return "test_tool_response"

    return FunctionTool.from_function(mock_tool_fn, name="test_tool", description="A test tool")


@pytest.fixture(name="llm_link")
def test_llm_link():
    return LitellmLLMLink(model="vertex_ai/gemini-2.5-flash")
