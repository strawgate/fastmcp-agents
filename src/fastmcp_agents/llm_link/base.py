"""Base classes and protocols for LLM links."""

import logging
from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from fastmcp.tools import Tool as FastMCPTool
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastmcp_agents.conversation.types import AssistantConversationEntry, Conversation
from fastmcp_agents.observability.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("llm_link")

class ModelProtocolMeta(type(BaseModel), type(Protocol)):
     pass

class CompletionMetadata(BaseModel):
    """Metadata about the completion."""

    token_usage: int | None = Field(default=None, description="The number of tokens used by the LLM.")
    """The number of tokens used by the LLM."""


class LLMLinkSettings(BaseSettings):
    """Settings for LLM links."""

    model_config = SettingsConfigDict(use_attribute_docstrings=True)

    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    """The temperature to use."""

    model: str = Field(default=...)
    """The model to use."""


@runtime_checkable
class LLMLinkProtocol(Protocol):
    """Protocol for LLM links."""

    async def async_completion(
        self,
        conversation: Conversation,
        fastmcp_tools: Sequence[FastMCPTool],
    ) -> AssistantConversationEntry: ...

    """Call the LLM with the given messages and tools.

    Args:
        conversation: The conversation to send to the LLM.
        fastmcp_tools: The tools to use.

    Returns:
        The assistant conversation entry.
    """

    def get_token_usage(self) -> int: ...
    """Get the number of tokens used by the LLM."""


class BaseLLMLink(BaseModel, metaclass=ModelProtocolMeta):
    """Base class for all LLM links.

    This class is used to abstract the LLM link implementation from the agent.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    llm_link_settings: LLMLinkSettings = Field(default_factory=lambda: LLMLinkSettings())
    """The settings to use for the LLM link."""

    completion_kwargs: dict[str, Any] = Field(default_factory=dict)
    """The kwargs to pass to the underlying LLM SDK when asking for a completion."""

    token_usage: int = Field(default=0)
    """The number of tokens used by the LLM."""

    logger: logging.Logger = Field(default_factory=lambda: logger)
    """The logger to use for the LLM link."""

    def get_token_usage(self) -> int:
        """Get the number of tokens used by the LLM."""
        return self.token_usage