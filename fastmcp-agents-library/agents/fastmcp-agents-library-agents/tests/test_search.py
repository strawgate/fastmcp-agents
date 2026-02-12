import pytest
from pydantic_evals import Case

from fastmcp_agents.library.agents.search.agents import search_agent
from tests.conftest import AgentRunInput, evaluate_agent_case


@pytest.mark.parametrize(
    ("user_prompt", "criteria"),
    [
        (
            "What job does Bill Easton have at Elastic? Where was he born?",
            ("The Agent Performs a web search and discovers that Bill Easton works in Product Management at Elastic"),
        ),
    ],
    ids=["Bill Easton"],
)
async def test_search(user_prompt: str, criteria: str):
    case = Case(
        inputs=AgentRunInput(
            deps=None,
            user_prompt=user_prompt,
        ),
    )
    await evaluate_agent_case(
        agent=search_agent,
        case=case,
        criteria=criteria,
    )
