from typing import Any

from fastmcp.mcp_config import MCPConfig, MCPServerTypes


def get_mcp_config(mcp: MCPConfig | dict[str, MCPServerTypes] | dict[str, Any]) -> MCPConfig:
    """Get the MCP config."""

    if isinstance(mcp, MCPConfig):
        return mcp

    return MCPConfig.model_validate(obj=mcp)
