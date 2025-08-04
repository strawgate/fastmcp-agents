from typing import TYPE_CHECKING

import pytest

from fastmcp_agents.library.agents.elasticsearch.agents import ask_esql_agent, ask_esql_expert
from fastmcp_agents.library.agents.elasticsearch.models import AskESQLExpertResponse

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult


def test_init_agents():
    assert ask_esql_expert is not None
    assert ask_esql_agent is not None


@pytest.mark.asyncio
async def test_call_agent():
    result: AgentRunResult[AskESQLExpertResponse] = await ask_esql_expert.run(
        user_prompt="What would i put in the `FROM` clause to target only metrics indices?",
        deps=None,
        output_type=AskESQLExpertResponse,
    )

    assert result is not None
    assert result.output is not None
    assert "FROM" in result.output.query
