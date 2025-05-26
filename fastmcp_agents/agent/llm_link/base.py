import logging
from typing import Any, Protocol

from mcp import Tool as MCPTool

from fastmcp_agents.agent.observability.logging import BASE_LOGGER
from fastmcp_agents.agent.types import AssistantConversationEntry, ToolCallRequest

logger = BASE_LOGGER.getChild("llm_link")


class AsyncLLMLink(Protocol):
    """Base class for all LLM links.

    This class is used to abstract the LLM link implementation from the agent.
    """

    completion_kwargs: dict[str, Any]
    """The kwargs to pass to the underlying LLM SDK when asking for a completion."""

    logger: logging.Logger = logger
    """The logger to use for the LLM link."""

    async def async_completion(
        self,
        messages: list,
        tools: list[MCPTool],
    ) -> tuple[AssistantConversationEntry, list[ToolCallRequest]]: ...

    """Call the LLM with the given messages and tools.

    Args:
        messages: The messages to send to the LLM.
        tools: The tools to use.
    """
