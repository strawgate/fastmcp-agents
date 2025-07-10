"""Custom errors for the loader."""

from fastmcp_agents.errors.base import FastMCPAgentsError


class LoaderError(FastMCPAgentsError):
    """Raised when there is an error loading the agent."""

    def __init__(self, message: str):
        self.message: str = message
        super().__init__(self.message)


class MCPServerStartupError(LoaderError):
    """Raised when a MCP server fails to start."""

    def __init__(self, server_name: str, error: Exception):
        self.message: str = f"MCP server '{server_name}' failed to start: {error}"
        super().__init__(self.message)
