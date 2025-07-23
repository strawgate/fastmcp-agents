import os
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest
from pydantic_ai import Agent

from fastmcp_agents.library.agent.documentation_maintainer.agent import (
    BestPracticesResponse,
    GatherDocumentationResponse,
    UpdateDocumentationResponse,
    best_practices_agent,
    do_it_all,
    gather_agent,
    update_agent,
)


@pytest.fixture
def best_practices() -> Agent[None, BestPracticesResponse]:
    return best_practices_agent


@pytest.fixture
def gather() -> Agent[None, GatherDocumentationResponse]:
    return gather_agent


@pytest.fixture
def update() -> Agent[None, UpdateDocumentationResponse]:
    return update_agent


def test_init(
    best_practices_agent: Agent[None, BestPracticesResponse],
    gather_agent: Agent[None, GatherDocumentationResponse],
    update_agent: Agent[None, UpdateDocumentationResponse],
):
    assert best_practices_agent
    assert gather_agent
    assert update_agent


@pytest.fixture
async def in_temp_dir():
    original_dir = Path.cwd()
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(path=temp_dir)
        try:
            yield temp_dir
        finally:
            os.chdir(path=original_dir)


@pytest.mark.asyncio
async def test_best_practices(best_practices: Agent[None, BestPracticesResponse], in_temp_dir: Path):
    Path("launcher\\readme.md").write_text(
        data=dedent(
            text="""The Launcher is a member of the Windom(tm) family of products.

            The launcher had the following features:
            - It can launch other programs
            - It can kill other programs
            - You can setup hotkeys to launch other programs

            The Launcher does not have the following features:
            - Run on macOS
            - Reliability

            It is MIT Licensed.

            Support is available in the GitHub Repository."""
        )
    )

    Path("reporter\\readme.md").write_text(
        data=dedent(
            text="""The Reporter is a member of the Windom(tm) family of products.

            The reporter had the following features:
            - It report on the utilization of other programs
            - It can monitor other programs and relaunch them if they crash
            - You can enable/disable the reporting of other programs
            - You can setup hotkeys to report on other programs

            The Reporter does not have the following features:
            - Run on macOS
            - Reliability

            It is MIT Licensed.

            Support is available in the GitHub Repository."""
        )
    )

    result = await best_practices.run(user_prompt="What are the best practices for readmes?")

    assert result.output.best_practices is not None

    assert len(result.output.best_practices) > 0


@pytest.mark.asyncio
@pytest.mark.skip_on_ci
async def test_best_practices_elastic_integrations(best_practices: Agent[None, BestPracticesResponse]):
    os.chdir(Path(__file__).parent.parent / "playground/es_integrations")

    result = await best_practices.run(user_prompt="What are the best practices for package readmes?")

    assert result.output.best_practices is not None

    assert len(result.output.best_practices) > 0


@pytest.mark.asyncio
@pytest.mark.skip_on_ci
async def test_gather_documentation_kafka(gather: Agent[None, GatherDocumentationResponse]):
    os.chdir(Path(__file__).parent.parent / "playground/es_integrations")

    result = await gather.run(user_prompt="Let's gather documentation to update the README.md in the Kafka package")

    assert result.output.sources is not None
    assert result.output.summary is not None


@pytest.mark.asyncio
@pytest.mark.skip_on_ci
async def test_update_documentation_kafka(update: Agent[None, UpdateDocumentationResponse]):
    os.chdir(Path(__file__).parent.parent / "playground/es_integrations")

    result = await update.run(user_prompt="Let's update the README.md in the Kafka package")

    assert result.output.changes is not None
    assert result.output.summary is not None


@pytest.mark.asyncio
@pytest.mark.skip_on_ci
async def test_do_it_all():
    os.chdir(Path(__file__).parent.parent / "playground/es_integrations")

    result = await do_it_all(task="Let's update the README.md in the Kafka package")

    assert result is not None
