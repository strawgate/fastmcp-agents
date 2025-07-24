"""
This agent is used to perform simple code tasks.
"""

import os
import tempfile
from pathlib import Path
from textwrap import dedent
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from fastmcp.tools.tool import Tool
from fastmcp_ai_agent_bridge.pydantic_ai import FastMCPToolset
from git import Repo
from pydantic import AnyHttpUrl, BaseModel, Field, RootModel
from pydantic_ai import Agent

from fastmcp_agents.library.agent.simple_code.helpers.filesystem import (
    get_structure,
    read_only_filesystem_mcp,
)

mcp_servers = {
    "filesystem": read_only_filesystem_mcp(),
}

toolset = FastMCPToolset.from_mcp_config(mcp_config=mcp_servers)

code_investigation_instructions = """
You are an expert software engineer. You are able to handle a wide variety of tasks related to software development.

Your goal is to study the assigned task, gather the necessary information to properly understand the task, and then
produce a viable plan to complete the task. You are to be thorough and do this right, you are not to concerned with
how much time it takes to complete the task.

You have access to the local filesystem, the tools you have available can search, summarize, and read files as needed.

For any task, it will be extremely important for you to gather the necessary information from the codebase:
1. Bug Fixes: If you are asked to fix a bug you will first understand the bug. You will review the different ways the relevant code
can be invoked and you will understand when and why the bug occurs and when and why it does not occur. You will first think
of a test that will fail if the bug is present and pass if the bug is not present. If the codebase includes tests, you will
write the test.

2. Propose a solution to a problem: If you are asked to propose a solution to a problem you will first understand the problem. You will
try to understand the cause of the problem.

3. Refactor code: If you are asked to plan a refactoring you will first understand the code. You will review the different areas of the code
that are relevant to the refactoring and you will understand how the different parts of the code interact. You will then propose a
refactoring plan.

4. Implement a new feature: If you are asked to implement a new feature you will first understand the feature. You will review the different
areas of the code that are relevant to the feature and you will understand how the different parts of the code interact. You will then
propose an implementation plan.

Once you believe you have completed the task you will step through the code line by line ensuring that the task is completed. If you have
not completed a part of the task, you will continue working on that part.

Once you have believe you have completed the task you will perform additional review of other files in the codebase, looking for any
references to the relevant code or tests that might need to be updated, or removed.

Remember, you cannot make any changes to the codebase. You can only read files.
"""


class FileLines(RootModel[list[str]]):
    """A file line with line number and content."""


class InvestigationFinding(BaseModel):
    """An investigation finding."""

    description: str
    file_path: str | None = None
    lines: FileLines = Field(default=..., description="The relevant lines of code in the file with their line numbers.")


class InvestigationRecommendation(BaseModel):
    """An investigation recommendation."""

    description: str
    action: Literal["fix", "refactor", "propose", "implement"]
    file_path: str | None = None
    current_lines: FileLines = Field(default=..., description="The relevant lines of code in the file with their line numbers.")
    proposed_lines: FileLines = Field(default=..., description="The proposed lines of code in the file with their line numbers.")


class InvestigationResponse(BaseModel):
    """An investigation response."""

    summary: str = Field(default=..., description="A summary of the findings. Under 1 page.")
    confidence: Literal["high", "medium", "low"] = Field(default=..., description="The confidence of the findings.")
    findings: list[InvestigationFinding]
    recommendations: list[InvestigationRecommendation] = Field(
        default=..., description="Recommendations for next steps based on the findings."
    )


code_investigation_agent = Agent[None, InvestigationResponse](
    model=os.environ.get("MODEL"),
    toolsets=[
        # We will provide a directory-locked toolset at runtime
    ],
    system_prompt=code_investigation_instructions,
    output_type=InvestigationResponse,
    retries=2,
    output_retries=2,
)

server = FastMCP[Any](name="investigate-code-agent")

CODE_REPOSITORY_TYPE = Annotated[
    AnyHttpUrl | Path | None,
    Field(
        description=dedent(
            text="""
        The code repository to investigate.

        If a Git URL is provided, it will be cloned.
        A local path can also be provided.
        If neither is provided, the agent will look in the current working directory."""
        ).strip(),
    ),
]


async def investigate_code(task: str, code_repository: CODE_REPOSITORY_TYPE) -> InvestigationResponse:
    """Perform a code investigation."""

    with tempfile.TemporaryDirectory(delete=False) as temp_dir:
        # We only actually use the tempdir if we are cloning a git repository
        if isinstance(code_repository, AnyHttpUrl):
            Repo.clone_from(url=str(code_repository), to_path=temp_dir, single_branch=True, depth=1)
            code_repository = Path(temp_dir)
        if code_repository is None:
            code_repository = Path.cwd()

        directory_locked_toolset = FastMCPToolset.from_mcp_config(
            mcp_config={"filesystem": read_only_filesystem_mcp(root_dir=code_repository)}
        )

        structure = get_structure(root_dir=code_repository, max_results=10)

        repo_info = f"""
        We've called get_structure on your behalf, here were the initial results to get you started:
        {structure}
        """

        run_result = await code_investigation_agent.run(user_prompt=[task, repo_info], toolsets=[directory_locked_toolset])

        return run_result.output


investigate_code_tool = Tool.from_function(fn=investigate_code)

server.add_tool(tool=investigate_code_tool)


def run():
    """Run the agent."""
    server.run(transport="stdio")


if __name__ == "__main__":
    server.run(transport="sse")
