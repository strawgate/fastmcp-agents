from fastmcp.tools.tool_transform import ToolTransformConfig

from fastmcp_agents.core.agents.task import TaskAgent
from fastmcp_agents.core.models.server_builder import FastMCPAgents
from fastmcp_agents.library.agent.elasticsearch.shared import (
    base_elasticsearch_mcp,
    esql_instructions,
    formatting_instructions,
    knowledge_base_instructions,
    prepare_knowledge_base,
)
from fastmcp_agents.library.mcp.strawgate.knowledge_base_mcp import (
    read_write_knowledge_base_mcp,
)

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

elasticsearch_mcp = base_elasticsearch_mcp.model_copy()
elasticsearch_mcp.tools = {
    "esql_query": ToolTransformConfig(
        tags={"esql"},
    ),
    "summarize_data_streams": ToolTransformConfig(
        tags={"data_streams"},
    ),
    "indices_data_streams_stats": ToolTransformConfig(
        name="get_data_streams",
        tags={"data_streams"},
    ),
}
elasticsearch_mcp.include_tags = {"esql", "data_streams"}


mcp_servers = {
    "knowledge-base": read_write_knowledge_base_mcp,
    "strawgate-elasticsearch": elasticsearch_mcp,
}


class AskESQLAgent(TaskAgent):
    """An agent that can ask questions about Elasticsearch and ES|QL and will use
    the Knowledge Base and connected Elasticsearch server to answer questions."""

    name: str = "ask_esql_agent"

    instructions: str | None = f"""
    {esql_instructions}
    {elasticsearch_instructions}
    {formatting_instructions}
    {knowledge_base_instructions}
    """


server = FastMCPAgents(
    name="ask-elasticsearch",
    mcp=mcp_servers,
    agents=[AskESQLAgent()],
).to_server()

if __name__ == "__main__":
    import asyncio

    asyncio.run(prepare_knowledge_base(read_write_knowledge_base_mcp))

    server.run(transport="sse")
