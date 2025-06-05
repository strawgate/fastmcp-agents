"""Base custom errors for FastMCP Agents."""


class FastMCPAgentsError(Exception):
    """Base class for all FastMCPAgents errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ContributionsWelcomeError(FastMCPAgentsError):
    """Raised when someone else should work on a feature."""

    def __init__(self, feature: str):
        self.message = f"We would welcome a contribution implementing {feature}"
        super().__init__(self.message)


class UnknownToolCallError(FastMCPAgentsError):
    """Raised when a tool call is not known."""

    def __init__(self, tool_name: str, extra_info: str | None = None):
        self.message = f"Unknown tool call: {tool_name}"
        if extra_info:
            self.message += f" {extra_info}"
        super().__init__(self.message)


class UnsupportedFeatureError(FastMCPAgentsError):
    """Raised when a feature is not supported."""

    def __init__(self, feature: str):
        self.message = f"FastMCPAgents does not support the feature: {feature}"
        super().__init__(self.message)


class NoResponseError(FastMCPAgentsError):
    """Raised when a response is not received."""

    def __init__(self, missing_item: str, model: str):
        self.message = f"{missing_item} was missing in the response from {model}"
        super().__init__(self.message)
