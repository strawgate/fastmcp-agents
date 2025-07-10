"""Base classes and protocols for LLM links."""

import logging
from abc import ABC
from collections.abc import Sequence
from typing import Any, Protocol, override, runtime_checkable

from fastmcp.tools import Tool as FastMCPTool
from pydantic import BaseModel, Field

from fastmcp_agents.conversation.types import AssistantConversationEntry, Conversation
from fastmcp_agents.util.base_model import StrictBaseModel
from fastmcp_agents.util.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("llm_link")


class CompletionMetadata(StrictBaseModel):
    """Metadata about the completion."""

    token_usage: int | None = Field(default=None, description="The number of tokens used by the LLM.")
    """The number of tokens used by the LLM."""

    @classmethod
    def from_model_extra(cls, model_extra: dict[str, Any] | None) -> "CompletionMetadata":
        """Create a CompletionMetadata from a model extra."""
        if model_extra:  # noqa: SIM102
            if extra := model_extra.get("usage"):  # noqa: SIM102
                if total_tokens := extra.get("total_tokens"):  # pyright: ignore[reportAny]
                    return cls(token_usage=total_tokens)  # pyright: ignore[reportAny]

        return cls(token_usage=None)


class TokenCounter(BaseModel):
    """A counter for the number of tokens used by the LLM."""

    usage: int = Field(default=0, description="The number of tokens used by the LLM.")
    """The number of tokens used by the LLM."""


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

    """Get the total number of tokens used by the LLM Link."""


# class BaseLLMLinkSettings(BaseSettings):
#     """Settings for LLM links."""

#     model_config = SettingsConfigDict(use_attribute_docstrings=True)

#     temperature: float | None = Field(default=None, ge=0.0, le=2.0)
#     """The temperature to use."""

#     model: str = Field(default=...)
#     """The model to use."""


class BaseLLMLink(LLMLinkProtocol, ABC):
    """Base class for all LLM links.

    This class is used to abstract the LLM link implementation from the agent.
    """

    token_counter: TokenCounter
    """The counter for the number of tokens used by the LLM."""

    logger: logging.Logger
    """The logger to use for the LLM link."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        **kwargs: Any,  # pyright: ignore[reportAny]
    ):
        if logger is not None:
            self.logger = logger

        self.token_counter = TokenCounter()

        super().__init__(**kwargs)

    @override
    def get_token_usage(self) -> int:
        """Get the number of tokens used by the LLM."""
        return self.token_counter.usage
