import os
from pathlib import Path

import pytest
from pydantic_evals import Case

from fastmcp_agents.library.agents.shared.models.code_base import GitCodeBase, RemoteGitCodeBase
from fastmcp_agents.library.agents.simple_code.agents.read_code_agent import (
    ReadCodeAgentInput,
    read_code_agent,
)
from tests.conftest import AgentRunInput, evaluate_agent_case


@pytest.mark.parametrize(
    ("user_prompt", "criteria"),
    [
        (
            "Investigate the calculator identify any flaws with the code.",
            (
                "The Agent investigates the calculator, reads the code, tests, and readme and identifies at least one flaw. The "
                "response includes a specific line-by-line recommendation for resolving each flaw."
            ),
        ),
        (
            "Determine if the Readme is an accurate reflection of the code in the repository.",
            (
                "The Agent investigates the readme and the calculator code and determines that the readme does not accurately "
                "reflect the structure of the code. The Agent's response includes a specific line-by-line recommendation to update "
                "the readme to accurately reflect the structure of the code."
            ),
        ),
        (
            "Can `last_result` be removed from the calculator code? How would that work?",
            (
                "The Agent investigates the calculator code and determines that `last_result` can be removed from the code easily "
                "and that the calculator will still work without any changes in functionality. The Agent's response marks specific "
                "line-by-line changes that remove `last_result` and the updated code."
            ),
        ),
        (
            "A user has reported that the calculator crashes when dividing by zero. Please investigate.",
            (
                "The Agent investigates the calculator code and determines that the calculator raises a ValueError when dividing by zero. "
                "The Agent indicates that this is intentional behavior as dividing by zero is not a valid operation. The Agent "
                "does not recommend any changes to the code base but may suggest 1) a change to the documentation to indicate that "
                "division by zero is not a valid operation or 2) that the user's calling code (not the calculator) "
                "should use a try/catch to handle the division by zero exception."
            ),
        ),
    ],
    ids=["find flaws", "inaccurate readme", "remove last_result", "division by zero"],
)
async def test_read_code_agent_calculator(user_prompt: str, criteria: str):
    case = Case(
        inputs=AgentRunInput(
            deps=ReadCodeAgentInput(
                code_base=RemoteGitCodeBase(git_url="https://github.com/strawgate/fastmcp-agents-tests-e2e.git", git_branch="main")
            ),
            user_prompt=user_prompt,
        ),
    )
    await evaluate_agent_case(
        agent=read_code_agent,
        case=case,
        criteria=criteria,
    )


@pytest.fixture
def beats_codebase() -> Path | None:
    if not (path := os.environ.get("BEATS_CODEBASE_PATH")):
        msg = "BEATS_CODEBASE_PATH is not set"
        raise ValueError(msg)

    return Path(path)


@pytest.mark.skipif(os.environ.get("BEATS_CODEBASE_PATH") is None, reason="BEATS_CODEBASE_PATH is not set")
@pytest.mark.parametrize(
    ("user_prompt", "criteria"),
    [
        (
            "Investigate the beats codebase and report the names of the Beats that are currently in the codebase. ",
            (
                "The Agent investigates the beats codebase and identifies "
                "agentbeat, winlogbeat, packetbeat, filebeat, auditbeat, dockerlogbeat, osquerybeat, and heartbeat."
                "It's okay for it to omit agentbeat, osquerybeat, and dockerlogbeat."
            ),
        ),
        (
            "What are the default output settings for the Elasticsearch and Kafka outputs in the Beats codebase? ",
            (
                "The Agent investigates the beats codebase and identifies the default output settings for the Elasticsearch "
                "and Kafka outputs. It reports that the default max bulk size for Elasticsearch is 1600 events."
            ),
        ),
        (
            "How do Beats perform self-monitoring and self-observability? Do all of the Beats do it the same way?",
            (
                "The Agent examines the implementation and identifies that Beats have a self-monitoring pipeline which collects "
                "metrics, health checks, and diagnostics. The Agent identifies that the self-monitoring pipeline is implemented "
                "in a similar way for all of the Beats."
            ),
        ),
        (
            (
                "A recent profiling of the code showed high time in the Elasticsearch Output, please recommend improvements to enhance "
                "performance and reduce garbage collection time."
            ),
            (
                "The agent reviews the Elasticsearch output and makes recommendations including using `sync.Pool` (or reusing buffers), not "
                " using `bytes.Buffer`, as well as tuning settings in the Elasticsearch output."
            ),
        ),
    ],
)
async def test_read_code_agent_beats(user_prompt: str, criteria: str, beats_codebase: Path):
    case = Case(
        inputs=AgentRunInput(
            deps=ReadCodeAgentInput(code_base=GitCodeBase(path=beats_codebase)),
            kwargs={},
            user_prompt=user_prompt,
        ),
    )

    await evaluate_agent_case(
        agent=read_code_agent,
        case=case,
        criteria=criteria,
    )
