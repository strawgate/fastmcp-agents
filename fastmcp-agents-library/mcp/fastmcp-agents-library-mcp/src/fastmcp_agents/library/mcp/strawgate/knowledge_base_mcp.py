from fastmcp.client import Client
from fastmcp.mcp_config import MCPConfig, TransformingStdioMCPServer
from fastmcp.tools.tool_transform import ToolTransformConfig
from pydantic import BaseModel

read_write_knowledge_base_mcp = TransformingStdioMCPServer(
    command="uvx",
    args=["knowledge-base-mcp", "auto", "run"],
    tools={},
)

readonly_knowledge_base_mcp = read_write_knowledge_base_mcp.model_copy()
readonly_knowledge_base_mcp.tools = {
    "docs_query": ToolTransformConfig(
        tags={"documentation"},
    )
}
readonly_knowledge_base_mcp.include_tags = {"documentation"}


class SeedKnowledgeBaseRequest(BaseModel):
    knowledge_base: str
    seed_urls: list[str]
    overwrite: bool = False


async def seed_knowledge_base(kb_mcp: TransformingStdioMCPServer, knowledge_base_requests: list[SeedKnowledgeBaseRequest]) -> None:
    async with Client(transport=MCPConfig(mcpServers={"knowledge-base": kb_mcp})) as client:
        knowledge_bases = await client.call_tool("get_knowledge_bases")
        for knowledge_base_request in knowledge_base_requests:
            if knowledge_base_request.knowledge_base in knowledge_bases.data:
                if knowledge_base_request.overwrite:
                    _ = await client.call_tool("delete_knowledge_base", {"knowledge_base": knowledge_base_request.knowledge_base})
            else:
                return

            _ = await client.call_tool(
                "load_website",
                {
                    "knowledge_base": knowledge_base_request.knowledge_base,
                    "seed_urls": knowledge_base_request.seed_urls,
                    "background": False,
                },
            )
