import os
from textwrap import dedent

from pydantic_ai.agent import Agent
from pydantic_ai.tools import RunContext

from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPServerToolset
from fastmcp_agents.library.agents.elasticsearch.models import AskESQLAgentResponse, AskESQLExpertResponse
from fastmcp_agents.library.agents.elasticsearch.prompts import (
    elasticsearch_instructions,
    esql_instructions,
    formatting_instructions,
    knowledge_base_instructions,
)
from fastmcp_agents.library.mcp.strawgate.elasticsearch import elasticsearch_mcp

ask_esql_expert: Agent[None, AskESQLExpertResponse] = Agent[None, AskESQLExpertResponse](
    name="ESQL Expert",
    model=os.environ.get("MODEL"),
    instructions=dedent(
        text=f"""
        {esql_instructions}
        {formatting_instructions}
        {knowledge_base_instructions}
        """
    ),
    output_type=AskESQLExpertResponse,
)


ask_esql_agent = Agent(
    model=os.environ.get("MODEL"),
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


@ask_esql_agent.toolset(per_run_step=False)
async def elasticsearch_toolset(ctx: RunContext[None]) -> FastMCPServerToolset[None]:  # pyright: ignore[reportUnusedParameter]  # noqa: ARG001
    elasticsearch_mcp_server = elasticsearch_mcp()

    elasticsearch_mcp_server.include_tags = {"esql", "summarize", "tips"}

    return FastMCPServerToolset[None].from_mcp_server(name="elasticsearch", mcp_server=elasticsearch_mcp_server)
