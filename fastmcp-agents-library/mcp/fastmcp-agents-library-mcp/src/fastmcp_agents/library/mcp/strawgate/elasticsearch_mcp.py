from fastmcp.client import Client
from fastmcp.mcp_config import MCPConfig, TransformingStdioMCPServer
from fastmcp.tools.tool_transform import ToolTransformConfig
from pydantic import BaseModel
import os

def elasticsearch_mcp() -> TransformingStdioMCPServer:
    return TransformingStdioMCPServer(
    command="uvx",
    env={
        "ES_HOST": os.getenv("ES_HOST"),
        "ES_API_KEY": os.getenv("ES_API_KEY"),
    },
    args=[
        "strawgate-es-mcp",
    ],
    tools={},
)