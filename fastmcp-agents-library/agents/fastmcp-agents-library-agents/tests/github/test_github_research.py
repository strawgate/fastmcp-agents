import pytest
from pydantic_evals import Case

from fastmcp_agents.library.agents.github.agents.research_agent import (
    ResearchAgentDependency,
    github_research_agent,
)
from tests.conftest import AgentRunInput, evaluate_agent_case


@pytest.mark.parametrize(
    ("issue_number", "criteria"),
    [
        (
            12761,
            (
                "The Agent investigates the issue and identifies several related issues pointing out the same issue "
                "The agent should point referenced issues 12761 / pull requests 45887"
            ),
        ),
    ],
)
async def test_github_research_agent_beats(issue_number: int, criteria: str):
    dependency = ResearchAgentDependency.from_issue(
        owner="elastic",
        repo="beats",
        issue_number=issue_number,
    )

    case = Case(
        inputs=AgentRunInput(
            deps=dependency,
        ),
    )

    await evaluate_agent_case(
        agent=github_research_agent,
        case=case,
        criteria=criteria,
    )
