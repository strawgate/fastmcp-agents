"""Custom errors for LLM link."""

from fastmcp_agents.errors.base import FastMCPAgentsError


class ModelDoesNotSupportFunctionCallingError(FastMCPAgentsError):
    """Raised when a model does not support function calling."""

    def __init__(self, model: str):
        self.message: str = f"Model {model} does not support function calling"
        super().__init__(self.message)


class ModelDoesNotSupportThinkingError(FastMCPAgentsError):
    """Raised when a model does not support thinking."""

    def __init__(self, model: str):
        self.message: str = f"Model {model} does not support thinking"
        super().__init__(self.message)
