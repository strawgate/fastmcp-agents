import os

from fastmcp.mcp_config import TransformingStdioMCPServer


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
