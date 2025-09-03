import pytest
from pydantic_evals import Case

from fastmcp_agents.library.agents.shared.models.code_base import RemoteGitCodeBase
from fastmcp_agents.library.agents.simple_code.agents.write_code_agent import (
    CodeAgentInput,
    code_agent,
)
from tests.conftest import AgentRunInput, evaluate_agent_case


@pytest.mark.parametrize(
    ("user_prompt", "criteria"),
    [
        (
            "Update the Readme to accurately reflect the structure of the codebase. Do not make any other changes.",
            (
                "The Agent investigates the readme and the calculator code and updates the readme to reflect the actual structure of "
                "the code. The agent adds the changes to Git and commits them."
            ),
        ),
        (
            "Add a docstring to each function in the calculator.",
            (
                "The Agent investigates the calculator code and adds a docstring to each function. "
                "The agent adds the changes to Git and commits them."
            ),
        ),
        (
            "Refactor the calculator to no longer be a class.",
            (
                "The Agent investigates the calculator code and refactors the calculator to no longer be a class. "
                "With each calculation being a function instead of a method on a class. "
                "The Agent also updates the readme and tests. "
                "The Agent adds the changes to Git and commits them."
            ),
        ),
    ],
    ids=["update readme", "add docstrings", "not a class"],
)
async def test_write_code_agent_calculator(user_prompt: str, criteria: str):
    case = Case(
        inputs=AgentRunInput(
            deps=CodeAgentInput(
                code_base=RemoteGitCodeBase(git_url="https://github.com/strawgate/fastmcp-agents-tests-e2e.git", git_branch="main")
            ),
            user_prompt=user_prompt,
        ),
    )
    await evaluate_agent_case(
        agent=code_agent,
        case=case,
        criteria=criteria,
    )
