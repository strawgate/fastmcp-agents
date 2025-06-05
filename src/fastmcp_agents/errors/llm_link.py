"""Custom errors for LLM link."""

from fastmcp_agents.errors.base import FastMCPAgentsError


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


class ModelNotSetError(FastMCPAgentsError):
    """Raised when a model is not set."""

    def __init__(self):
        self.message = "MODEL environment variable is not set and no model was provided"
        super().__init__(self.message)
