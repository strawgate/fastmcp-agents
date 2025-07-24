import json
import os
from pathlib import Path
from textwrap import dedent
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.tools.tool import Tool
from fastmcp_ai_agent_bridge.pydantic_ai import FastMCPToolset
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult

from fastmcp_agents.library.agent.documentation_maintainer.logging import configure_console_logging
from fastmcp_agents.library.mcp.nickclyde import duckduckgo_mcp
from fastmcp_agents.library.mcp.strawgate import (
    read_only_filesystem_mcp,
    read_only_knowledge_base_mcp,
    read_write_filesystem_mcp,
    read_write_knowledge_base_mcp,
)

best_practices_servers = {
    "file-system": read_only_filesystem_mcp(),
}

gather_mcp_servers = {
    "file-system": read_only_filesystem_mcp(),
    "knowledge-base": read_write_knowledge_base_mcp(),
    "duckduckgo": duckduckgo_mcp(),
}

update_mcp_servers = {
    "file-system": read_write_filesystem_mcp(),
    "knowledge-base": read_only_knowledge_base_mcp(),
}

gather_toolset: FastMCPToolset[None] = FastMCPToolset.from_mcp_config(mcp_config=gather_mcp_servers)
update_toolset: FastMCPToolset[None] = FastMCPToolset.from_mcp_config(mcp_config=update_mcp_servers)
best_practices_toolset: FastMCPToolset[None] = FastMCPToolset.from_mcp_config(mcp_config=best_practices_servers)


class BestPracticeExample(BaseModel):
    """An example of a best practice."""

    example: str = Field(description="A verbatim example of the best practice from the sampled documentation.")
    example_source: str = Field(description="The source of the example")


class BestPractice(BaseModel):
    """A Best Practice."""

    name: str = Field(description="The name of the best practice.")
    description: str = Field(description="A description of the best practice.")
    requirements: list[str] = Field(description="A list of requirements for the best practice.")
    examples: list[BestPracticeExample] = Field(description="A list of examples of the best practice.")


class BestPracticesResponse(BaseModel):
    """The response from the best practices agent."""

    best_practices: list[BestPractice] = Field(
        description="A detailed list of best practices that exist across the documentation you reviewed."
    )


best_practices_agent = Agent(
    model=os.environ.get("MODEL"),
    toolsets=[best_practices_toolset],
    output_type=BestPracticesResponse,
    instructions=dedent(
        text="""You are a best practices agent. You are responsible for producing a `best practices` file related to types
    of documentation. You will be given a specific set of documentation to review, like `README.md` files. You will first review the
    specific documentation and then you will find and review similar documentation in the project.

    You will return a `best practices` summary that is a list of `best practices` that exist across the documentation you reviewed.

    You will check the size of files you are reviewing and you will ensure that you do not review more than 2 megabytes of documentation.

    If the user requests a thorough summary, you will check for additional files/examples and your best practices should be very detailed,
    not just a list of simple sentences

    If the user requests a brief summary, previewing the files/examples is sufficient and your best practices should be a list of
    simple sentences
    """
    ),
)


class GatherDocumentationSource(BaseModel):
    """A source of documentation."""

    name: str = Field(description="The name of the source.")
    url: str = Field(description="The url of the source.")
    reason: str = Field(description="The reason you gathered this source.")


class GatherDocumentationResponse(BaseModel):
    """The response from the gather documentation tool."""

    summary: str = Field(description="A summary of the documentation you gathered.")
    sources: list[GatherDocumentationSource] = Field(description="A list of sources used to gather the documentation.")


gather_agent = Agent(
    model=os.environ.get("MODEL"),
    output_type=GatherDocumentationResponse,
    instructions="""
    You are a documentation gathering agent. You are responsible for helping to update documenation in a project
    repository. You will be given a specific set of documentation to update.

    You will:
    1. begin by reviewing the current documentation using the filesystem tools along with similar documentation in the repository to
       understand what "good" should look like.
    2. review the list of current documentation by checking the existing knowledge bases via the `get_knowledge_bases` tool. If you find
       that the documentation is already present in the knowledge base, you can end and report success.
    3. Otherwise, use the web search tool to find the most relevant online documentation, prefering vendor documentation over
       general documentation.
    4. use the knowledge base `load_website` tool to crawl and index the relevant documentation. The `load_website` tool will gather child
       pages so ensure the seed_url you provide ends with a slash. If you provide a seed_url, there is no need to provide
       subpages, they will automatically be included.

    You will return a summary of the documentation and the sources used to gather the documentation.
    """,
)


class UpdateDocumentationResponse(BaseModel):
    """The response from the update documentation tool."""

    summary: str = Field(description="A summary of the changes you made to the documentation.")
    changes: list[str] = Field(description="A list of changes you made to the documentation.")


update_agent = Agent(
    model=os.environ.get("MODEL"),
    output_type=UpdateDocumentationResponse,
    retries=3,
    output_retries=3,
    instructions=dedent(
        text="""
        You are a documentation updating agent. You are responsible for updating the documentation in a project repository.
        You will be given a specific set of documentation to update along with a list of gathered documentation you can query
        and a list of best practices you should follow.

        You will:
        1. review the best practices and the gathered documentation
        2. query the knowledge base with questions ranging from high level questions about the product from the vendor down tos
           specific questions about what the product does, how to troubleshoot it, how to use it, etc. Anything that might be helpful
           to have while updating the documentation. You can perform as many queries as you need to and you should generally plan on
           performing 5-10 queries.
        3. update the documentation in the repository
        4. return a summary of the documentation you updated
        """
    ),
)

fastmcp_server: FastMCP[Any] = FastMCP(name="documentation-maintainer")

output_dir = Path("output")
if not output_dir.exists():
    output_dir.mkdir(parents=True)


def record_result(run_result: AgentRunResult[Any], name: str) -> None:
    """Record the result of an agent run."""
    output_file = output_dir / f"{name}.json"
    if isinstance(run_result.output, BaseModel):
        _ = output_file.write_text(run_result.output.model_dump_json())
    else:
        _ = output_file.write_text(str(json.dumps(run_result.output)))


@fastmcp_server.tool
async def gather_documentation(task: str) -> GatherDocumentationResponse:
    """Gather documentation from the file system and knowledge base."""
    run_result: AgentRunResult[GatherDocumentationResponse] = await gather_agent.run(user_prompt=task)

    record_result(run_result, "gather_documentation")

    return run_result.output


@fastmcp_server.tool
async def update_documentation(task: str) -> UpdateDocumentationResponse:
    """Update documentation in the file system."""
    run_result: AgentRunResult[UpdateDocumentationResponse] = await update_agent.run(user_prompt=task)

    record_result(run_result, "update_documentation")

    return run_result.output


@fastmcp_server.tool
async def best_practices(task: str, depth: Literal["thorough", "normal", "brief"] = "thorough") -> BestPracticesResponse:
    """Get best practices for documentation."""
    run_result: AgentRunResult[BestPracticesResponse] = await best_practices_agent.run(
        user_prompt=[
            task,
            f"The requester has asked that you produce a {depth} summary of best practices.",
        ],
        toolsets=[best_practices_toolset],
    )

    record_result(run_result, "best_practices")

    return run_result.output


async def do_it_all(task: str) -> str:
    """Do it all."""

    print(f"Running best practices agent with task: {task}")
    async with best_practices_agent:
        best_practices_run_result: AgentRunResult[BestPracticesResponse] = await best_practices_agent.run(user_prompt=task)

    record_result(best_practices_run_result, "best_practices")

    gather_task = f"""
    The best practices for documentation are, this may inform what you should gather:
    ```md
    {best_practices_run_result.output.best_practices}
    ```
    """

    print("Running gather agent with task: {gather_task}")
    async with gather_agent:
        gather_run_result: AgentRunResult[GatherDocumentationResponse] = await gather_agent.run(
            user_prompt=[gather_task, task], toolsets=[gather_toolset]
        )

    record_result(gather_run_result, "gather_documentation")

    update_task = f"""
    The best practices for documentation are (this may inform what you should gather):
    ```md
    {best_practices_run_result.output.best_practices}
    ```
    the gathered documentation is:
    ```md
    Documentation is available in the knowledge base.
    ```
    """

    print("Running update agent with task: {update_task}")
    async with update_agent:
        update_run_result: AgentRunResult[UpdateDocumentationResponse] = await update_agent.run(
            user_prompt=[update_task, task], toolsets=[update_toolset]
        )

    record_result(update_run_result, "update_documentation")

    return f"""
    Gather Documentation:
    {gather_run_result.output.summary}
    Best Practices:
    {best_practices_run_result.output.best_practices}
    Updated Documentation:
    {update_run_result.output.summary}
    """


do_it_all_tool = Tool.from_function(do_it_all)
fastmcp_server.add_tool(do_it_all_tool)

server = fastmcp_server

if __name__ == "__main__":
    configure_console_logging()

    fastmcp_server.run(transport="sse")
