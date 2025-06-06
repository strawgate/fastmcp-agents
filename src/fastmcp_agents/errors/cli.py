"""Custom errors for the CLI."""

from fastmcp_agents.errors.base import FastMCPAgentsError


class NoServerToWrapError(FastMCPAgentsError):
    """Raised when no server is provided to wrap."""

    def __init__(self):
        self.message = "No server provided to wrap"
        super().__init__(self.message)


class MultipleConfigOptionsError(FastMCPAgentsError):
    """Raised when multiple config options are provided."""

    def __init__(self):
        self.message = "Only one of config-file, config-url, or config-bundled can be provided"
        super().__init__(self.message)


class NoConfigError(FastMCPAgentsError):
    """Raised when no config is provided."""

    def __init__(self):
        self.message = "No config provided"
        super().__init__(self.message)


class MCPServerError(FastMCPAgentsError):
    """Raised when an MCP server fails to wrap."""

    def __init__(self, server: str):
        self.message = f"Error wrapping MCP server {server}"
        super().__init__(self.message)


class MCPServerStartupError(FastMCPAgentsError):
    """Raised when an MCP server fails to start."""

    def __init__(self, server: str):
        self.message = f"Error starting MCP server {server}"
        super().__init__(self.message)
