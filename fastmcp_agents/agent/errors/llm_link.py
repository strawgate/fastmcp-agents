from fastmcp_agents.agent.errors.base import FastMCPAgentsError


class ModelDoesNotSupportFunctionCallingError(FastMCPAgentsError):
    """Raised when a model does not support function calling."""

    def __init__(self, model: str):
        self.message = f"Model {model} does not support function calling"
        super().__init__(self.message)


class ModelDoesNotExistError(FastMCPAgentsError):
    """Raised when a model does not exist."""

    def __init__(self, model: str):
        self.message = f"Model {model} does not exist"
        super().__init__(self.message)
