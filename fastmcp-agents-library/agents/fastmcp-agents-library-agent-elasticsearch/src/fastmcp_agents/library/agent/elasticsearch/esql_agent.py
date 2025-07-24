import os
from textwrap import dedent
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP
from fastmcp.tools.tool import Tool
from fastmcp_ai_agent_bridge.pydantic_ai import FastMCPToolset
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from fastmcp_agents.library.agent.elasticsearch.shared import (
    esql_elasticsearch_mcp,
    esql_instructions,
    formatting_instructions,
    knowledge_base_instructions,
    prepare_knowledge_base,
)
from fastmcp_agents.library.mcp.strawgate import (
    read_only_knowledge_base_mcp,
    read_write_knowledge_base_mcp,
)

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult

elasticsearch_instructions = """
You have access to the Elasticsearch MCP Server to perform queries so you can verify the indices, fields, mappings and more:
1. Call indices_data_streams_stats to get a list of data streams
2. For interesting datastreams, call summarize_data_stream, providing the list of datastreams you're interested in more information about
    This will provide a summary of fields along with sample data for each field and some sample documents.

You should always run any ES|QL query you write for a task and make sure it works. In addition to answering the specific question asked,
you should always provide a markdown formatted response with a small set of actual results of the query for the user to see. When providing
this small set of actual results, you should include the results as a markdown formatted table as they were returned from the query without
removing any fields.

If the user asks you a specific question, like how many of X are there, you should run a query to get the answer but you should
also provide the full query, explanation, documentation links, and results in your response unless specifically asked not to.
"""

server = FastMCP[None](name="ask-esql-agent")

mcp_servers = {
    "knowledge-base": read_only_knowledge_base_mcp(),
    "strawgate-elasticsearch": esql_elasticsearch_mcp(),
}

ask_esql_toolset = FastMCPToolset.from_mcp_config(mcp_config=mcp_servers)


class QueryExplanation(BaseModel):
    """The explanation of a query."""

    step: str = Field(description="The step of the query. Each pipe `|` is a step.")
    explanation: str = Field(description="The explanation of the step.")
    reference: str = Field(description="A reference to the documentation for the step.")


class AskESQLAgentResponse(BaseModel):
    """The response from the ask_esql_agent."""

    answer: str = Field(description="A summary of the results of the query.")
    query: str = Field(description="The query that was run.")
    explanation: list[QueryExplanation] = Field(description="The explanation of the query.")
    results: list[dict[str, Any]] = Field(description="The results of the query.")


ask_esql_agent = Agent(
    model=os.environ.get("MODEL"),
    toolsets=[ask_esql_toolset],
    instructions=dedent(
        text=f"""
        {esql_instructions}
        {elasticsearch_instructions}
        {formatting_instructions}
        {knowledge_base_instructions}
        """
    ),
    output_type=AskESQLAgentResponse,
)


async def ask_esql_agent_fn(question: str) -> AskESQLAgentResponse:
    """Ask an ESQL question."""

    async with ask_esql_agent:
        esql_tips: Any = await ask_esql_toolset.call_tool_direct(name="esql_tips", tool_args={})
        run_result: AgentRunResult[AskESQLAgentResponse] = await ask_esql_agent.run(
            user_prompt=[str(esql_tips), question],
            toolsets=[ask_esql_toolset],
        )

        return run_result.output


ask_esql_tool = Tool.from_function(fn=ask_esql_agent_fn, name="ask_esql_agent")
server.add_tool(tool=ask_esql_tool)


def run():
    """Run the agent."""
    server.run(transport="stdio")


if __name__ == "__main__":
    import asyncio

    asyncio.run(prepare_knowledge_base(knowledge_base_mcp=read_write_knowledge_base_mcp()))

    server.run(transport="sse")
