from typing import Any, override

from fastmcp.mcp_config import MCPConfig, MCPServerTypes
from pydantic import Field

from fastmcp_agents.core.agents.task import DefaultFailureModel, DefaultSuccessModel, TaskAgent
from fastmcp_agents.core.models.server_builder import FastMCPAgents
from fastmcp_agents.library.agent.elasticsearch.shared import (
    esql_instructions,
    formatting_instructions,
    knowledge_base_instructions,
    prepare_knowledge_base,
)
from fastmcp_agents.library.mcp.strawgate.knowledge_base_mcp import (
    read_only_knowledge_base_mcp,
    read_write_knowledge_base_mcp,
)

mcp_servers: dict[str, MCPServerTypes] = {
    "knowledge-base": read_only_knowledge_base_mcp(),
}


class AskESQLExpert(TaskAgent):
    """An agent that can ask questions about Elasticsearch and ES|QL and will use
    the Knowledge Base to answer questions."""

    name: str = "ask_esql_agent"
    instructions: str = f"""
    {formatting_instructions}
    {esql_instructions}
    {knowledge_base_instructions}
    """

    mcp: MCPConfig | dict[str, MCPServerTypes] | dict[str, Any] | None = Field(default=mcp_servers)

    @override
    async def __call__(self, task: str) -> DefaultSuccessModel | DefaultFailureModel:
        """Call the agent."""
        return await super().handle_task(task=task)


server = FastMCPAgents(
    name="ask-elasticsearch",
    mcp=mcp_servers,
    agents=[AskESQLExpert(tools_from_context=True)],
).to_server()

if __name__ == "__main__":
    import asyncio

    asyncio.run(prepare_knowledge_base(read_write_knowledge_base_mcp()))

    server.run(transport="sse")
