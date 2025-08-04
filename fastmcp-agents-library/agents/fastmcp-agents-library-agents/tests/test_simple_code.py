from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import BaseModel
from pydantic_ai.agent import AgentRunResult
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from fastmcp_agents.library.agents.shared.models import Failure
from fastmcp_agents.library.agents.simple_code.agents import (
    code_implementation_agent,
    code_investigation_agent,
)
from fastmcp_agents.library.agents.simple_code.models import ImplementationResponse, InvestigationResult

from .conftest import assert_passed, evaluation_rubric, split_dataset

if TYPE_CHECKING:
    from pydantic_evals.reporting import EvaluationReport


def test_init_agents():
    assert code_implementation_agent is not None

    assert code_investigation_agent is not None


calculator_code_base = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    return a / b

def power(a, b):
    return a ** b
"""

llm_judge = LLMJudge(
    score={"evaluation_name": "investigation", "include_reason": True},
    include_input=True,
    rubric=evaluation_rubric(criteria="The completed investigation matches the task posed to the agent."),
)


class CaseInput(BaseModel):
    user_prompt: str
    code_base: str

    def write_to_file(self, path: Path):
        path.write_text(self.code_base)


dataset = Dataset(
    evaluators=[
        LLMJudge(
            score={"evaluation_name": "investigation", "include_reason": True},
            include_input=True,
            rubric=evaluation_rubric(criteria="The completed investigation matches the task posed to the agent."),
        ),
    ],
    cases=[
        Case(
            name="docs",
            inputs=CaseInput(user_prompt="Please add a docstring to each function in the calculator.", code_base=calculator_code_base),
        ),
        Case(
            name="refactor",
            inputs=CaseInput(user_prompt="Please refactor the calculator to be a class.", code_base=calculator_code_base),
        ),
    ],
)


dataset_names, datasets = split_dataset(dataset)


@pytest.mark.parametrize("dataset", datasets, ids=dataset_names)
async def test_investigation_cases(dataset: Dataset, temp_dir: Path):
    code_path: Path = temp_dir / "sample_code.py"

    async def run_code_investigation_agent(case_input: CaseInput) -> AgentRunResult[InvestigationResult | Failure]:
        case_input.write_to_file(code_path)

        return await code_investigation_agent.run(user_prompt=case_input.user_prompt, deps=temp_dir)

    evaluation: EvaluationReport[InvestigationResult | Failure, Any, Any] = await dataset.evaluate(
        task=run_code_investigation_agent,
        name="GitHub Agent",
    )

    assert_passed(evaluation_report=evaluation)


@pytest.mark.parametrize("dataset", datasets, ids=dataset_names)
async def test_implementation_cases(dataset: Dataset, temp_dir: Path):
    code_path: Path = temp_dir / "sample_code.py"

    async def run_code_agent(case_input: CaseInput) -> AgentRunResult[ImplementationResponse | Failure]:
        case_input.write_to_file(code_path)

        return await code_implementation_agent.run(user_prompt=case_input.user_prompt, deps=temp_dir)

    evaluation: EvaluationReport[ImplementationResponse | Failure, Any, Any] = await dataset.evaluate(
        task=run_code_agent,
        name="GitHub Agent",
    )

    assert_passed(evaluation_report=evaluation)
