"""Custom errors for agents."""

from fastmcp_agents.errors.base import FastMCPAgentsError


class ToolNotFoundError(FastMCPAgentsError):
    def __init__(self, agent_name: str, tool_name: str):
        self.message: str = f"Agent '{agent_name}' tried calling tool '{tool_name}' but it was not found"
        super().__init__(self.message)


class NoResponseError(FastMCPAgentsError):
    def __init__(self, agent_name: str):
        self.message: str = f"Agent '{agent_name}' did not return a response"
        super().__init__(self.message)
