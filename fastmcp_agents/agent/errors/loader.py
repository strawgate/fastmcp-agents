from fastmcp_agents.agent.errors.base import FastMCPAgentsError


class LoaderError(FastMCPAgentsError):
    """Raised when there is an error loading the agent."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class ToolsNotFoundError(LoaderError):
    """Raised when a tool is not found."""

    def __init__(self, agent_name: str, missing_tools: set[str]):
        self.message = f"Agent '{agent_name}' is missing {len(missing_tools)} tools: {missing_tools}"
        super().__init__(self.message)
