from textwrap import dedent
from typing import Annotated, Any, Literal, override

from pydantic import BaseModel, Field

from fastmcp_agents.core.agents.base import DefaultFailureModel
from fastmcp_agents.core.models.server_builder import FastMCPAgents, yaml
from fastmcp_agents.library.agent.simple_code.base import BaseCodeAgent
from fastmcp_agents.library.agent.simple_code.helpers.filesystem import (
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


class ImplementationResponse(BaseModel):
    """A response from the implementation agent."""

    summary: str
    confidence: Literal["low", "medium", "high"]


class CodeImplementationAgent(BaseCodeAgent):
    """An agent that can implement code."""

    name: str = "ask_code_implementation_agent"

    instructions: str = code_implementation_instructions

    mcp: dict[str, Any] | None = Field(
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
    ) -> ImplementationResponse | DefaultFailureModel:
        """Perform a code investigation."""

        async with self.prepare_workspace(git_url=git_url) as (_, structure):
            agent_task = dedent("""
            The codebase in the current working directory:

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

            return await self.handle_task(task=agent_task, success_model=ImplementationResponse)


server = FastMCPAgents(
    name="implement-code-agent",
    mcp=mcp_servers,
    agents=[CodeImplementationAgent(mcp=None)],
).to_server()

if __name__ == "__main__":
    server.run()
