from fastmcp.mcp_config import TransformingStdioMCPServer


def duckduckgo_mcp() -> TransformingStdioMCPServer:
    return TransformingStdioMCPServer(
        command="uvx",
        args=[
            "duckduckgo-mcp-server",
        ],
        tools={},
    )
