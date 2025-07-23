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
from pydantic_ai.agent import Agent

from fastmcp_agents.library.agent.simple_code.helpers.filesystem import (
    get_structure,
    read_write_filesystem_mcp,
)

code_implementation_instructions = """
You are an expert software engineer. You are able to handle a wide variety of tasks related to software development.

Your goal is to study the assigned task, gather the necessary information to properly understand the task,
produce a viable plan to complete the task and then execute the plan.

You have access to the local filesystem, the tools you have available can search, summarize, create, read, update, and delete
files and directories as needed.

For any task, it will be extremely important for you to gather the necessary information from the codebase:
1. Bug Fixes: If you are asked to fix a bug you will first understand the bug. You will review the different ways the relevant code
can be invoked and you will understand when and why the bug occurs and when and why it does not occur. You will first think
of a test that will fail if the bug is present and pass if the bug is not present. If the codebase includes tests, you will
write the test.

2. Propose a solution to a problem: If you are asked to propose a solution to a problem you will first understand the problem. You will
try to understand the cause of the problem.

3. Refactor code: If you are asked to refactor code you will first understand the code. You will review the different areas of the code
that are relevant to the refactoring and you will understand how the different parts of the code interact. You will then propose a
refactoring plan.

4. Implement a new feature: If you are asked to implement a new feature you will first understand the feature. You will review the different
areas of the code that are relevant to the feature and you will understand how the different parts of the code interact. You will then
propose an implementation plan.

If the plan is more than a couple steps, you will then write the plan to a Markdown file called `plan.md`. You will read this plan after
writing it to ensure that it accurately reflects the plan. Once you have a plan, you will execute the plan performing the necessary steps
to complete the task.

Once you believe you have completed the task you will step through the code line by line ensuring that the task is completed. You will
re-read the written plan to make sure you have not missed any steps. When calling report_task_success you will enumerate the action you
took to resolve each part of the task. If you have not completed a part of the task, you will continue working on that part.
"""

mcp_servers = {
    "filesystem": read_write_filesystem_mcp(),
}


class FileLines(RootModel[list[str]]):
    """A file line with line number and content."""


class PotentialFlaw(BaseModel):
    """A potential flaw in the code."""

    description: str
    file_path: str | None = None
    lines: FileLines = Field(default=..., description="The relevant lines of code in the file with their line numbers.")


class ImplementationResponse(BaseModel):
    """A response from the implementation agent."""

    summary: str
    confidence: Literal["low", "medium", "high"]
    potential_flaws: list[PotentialFlaw] = Field(
        default=..., description="A list of potential flaws in the code that a reviewer should review before merging."
    )


code_implementation_agent: Agent[None, ImplementationResponse] = Agent[None, ImplementationResponse](
    model=os.environ.get("MODEL"),
    toolsets=[
        # We will provide a directory-locked toolset at runtime
    ],
    system_prompt=code_implementation_instructions,
    output_type=ImplementationResponse,
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


async def implement_code(task: str, code_repository: CODE_REPOSITORY_TYPE) -> ImplementationResponse:
    """Perform a code investigation."""

    with tempfile.TemporaryDirectory(delete=False) as temp_dir:
        # We only actually use the tempdir if we are cloning a git repository
        if isinstance(code_repository, AnyHttpUrl):
            Repo.clone_from(url=str(code_repository), to_path=temp_dir, single_branch=True, depth=1)
            code_repository = Path(temp_dir)
        if code_repository is None:
            code_repository = Path.cwd()

        directory_locked_toolset = FastMCPToolset.from_mcp_config(
            mcp_config={"filesystem": read_write_filesystem_mcp(root_dir=code_repository)}
        )

        structure = get_structure(root_dir=code_repository, max_results=10)

        repo_info = f"""
        We've called get_structure on your behalf, here were the initial results to get you started:
        {structure}
        """

        run_result = await code_implementation_agent.run(user_prompt=[task, repo_info], toolsets=[directory_locked_toolset])

        return run_result.output


implement_code_tool = Tool.from_function(fn=implement_code)

server.add_tool(tool=implement_code_tool)

if __name__ == "__main__":
    server.run(transport="sse")
