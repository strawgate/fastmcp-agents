"""
This agent is used to perform simple code tasks.
"""

from textwrap import dedent
from typing import Annotated, Any, override

from pydantic import BaseModel, Field

from fastmcp_agents.core.agents.base import DefaultFailureModel
from fastmcp_agents.core.models.server_builder import FastMCPAgents, yaml
from fastmcp_agents.library.agent.simple_code.base import BaseCodeAgent
from fastmcp_agents.library.agent.simple_code.helpers.filesystem import (
    read_only_filesystem_mcp,
)

mcp_servers = {
    "filesystem": read_only_filesystem_mcp(),
}

code_investigation_instructions = """
You are an expert software engineer. You are able to handle a wide variety of tasks related to software development.

Your goal is to study the assigned task, gather the necessary information to properly understand the task, and then
produce a viable plan to complete the task.

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

Once you believe you have completed the task you will step through the code line by line ensuring that the task is completed. You will
re-read the written plan to make sure you have not missed any steps. When calling report_task_success you will enumerate the action you
took to resolve each part of the task. If you have not completed a part of the task, you will continue working on that part.

Remember, you cannot make any changes to the codebase. You can only read files.
"""


class InvestigationFinding(BaseModel):
    """An investigation finding."""

    description: str
    file_path: str | None = None
    line_number: int | None = None
    line_content: str | None = None


class InvestigationResponse(BaseModel):
    """An investigation response."""

    summary: str
    findings: list[InvestigationFinding]


class CodeInvestigationAgent(BaseCodeAgent):
    """An agent that can perform simple code tasks."""

    name: str = "ask_code_investigation_agent"

    instructions: str | None = code_investigation_instructions

    mcp: dict[str, Any] | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        default=mcp_servers,
        description="The MCP servers to use for the agent.",
    )

    @override
    async def __call__(
        self,
        *,
        task: str,
        git_url: Annotated[
            str,
            """If a Git URL is provided, it will be cloned.
            If no Git URL is provided, the agent will look in the current working directory.""",
        ]
        | None = None,
    ) -> InvestigationResponse | DefaultFailureModel:
        """Perform a code investigation."""

        async with self.prepare_workspace(git_url=git_url) as (_, structure):
            agent_task = dedent("""
            The codebase in the current working directory.

            The codebase structure is:
            ```json
            {structure}
            ```

            The task is:
            ```
            {task}
            ```
            """).format(
                structure=yaml.safe_dump(structure, indent=2, sort_keys=False),
                task=task,
            )

            return await self.handle_task(task=agent_task, success_model=InvestigationResponse)


server = FastMCPAgents(
    name="investigate-code-agent",
    mcp=mcp_servers,
    agents=[CodeInvestigationAgent(mcp=None)],
).to_server()

if __name__ == "__main__":
    server.run(transport="sse")
