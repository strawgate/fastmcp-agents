"""Base classes and protocols for LLM links."""

import logging
from typing import Any, Protocol

from fastmcp.tools import Tool as FastMCPTool
from pydantic import BaseModel, Field

from fastmcp_agents.conversation.types import AssistantConversationEntry, Conversation
from fastmcp_agents.observability.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("llm_link")


class CompletionMetadata(BaseModel):
    """Metadata about the completion."""

    token_usage: int | None = Field(default=None, description="The number of tokens used by the LLM.")
    """The number of tokens used by the LLM."""


class AsyncLLMLink(Protocol):
    """Base class for all LLM links.

    This class is used to abstract the LLM link implementation from the agent.
    """

    completion_kwargs: dict[str, Any]
    """The kwargs to pass to the underlying LLM SDK when asking for a completion."""

    token_usage: int = 0
    """The number of tokens used by the LLM."""

    logger: logging.Logger = logger
    """The logger to use for the LLM link."""

    async def async_completion(
        self,
        conversation: Conversation,
        fastmcp_tools: list[FastMCPTool],
    ) -> AssistantConversationEntry: ...

    """Call the LLM with the given messages and tools.

    Args:
        conversation: The conversation to send to the LLM.
        fastmcp_tools: The tools to use.

    Returns:
        The assistant conversation entry.
    """
