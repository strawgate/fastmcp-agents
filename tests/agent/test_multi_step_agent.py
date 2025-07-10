import pytest
from fastmcp.tools import FunctionTool

from fastmcp_agents.agent.multi_step import DEFAULT_STEP_LIMIT, MultiStepAgent
from fastmcp_agents.llm_link.litellm import LitellmLLMLink


@pytest.fixture
def mock_tool():
    def mock_tool_fn():
        """A mock tool function."""
        return "test_tool_response"

    return FunctionTool.from_function(mock_tool_fn, name="test_tool", description="A test tool")


@pytest.fixture
def llm_link():
    return LitellmLLMLink(model="gpt-3.5-turbo")


def test_multi_step_agent_init(mock_tool, llm_link):
    """Test that a multi step agent can be initialized with the correct properties."""
    agent = MultiStepAgent(
        name="test_agent",
        description="A test agent",
        default_tools=[mock_tool],
        llm_link=llm_link,
    )

    assert agent.name == "test_agent"
    assert agent.description == "A test agent"
    assert len(agent.default_tools) == 1
    assert agent.llm_link is not None
    assert agent.step_limit == DEFAULT_STEP_LIMIT
