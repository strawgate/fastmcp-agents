from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar, override

from pydantic import BaseModel, ConfigDict, Field

from fastmcp_agents.core.completions.base import CompletionMessageType


class AgentRunContext(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True, use_attribute_docstrings=True)

    successful_tool_calls: list[str] = Field(default_factory=list, description="The names of the tools that were successful.")
    messages: list[CompletionMessageType] = Field(default_factory=list, description="The messages that were sent to the agent.")
    failed_tool_calls: list[str] = Field(default_factory=list, description="The names of the tools that failed.")
    auto_start: bool = Field(default=True, description="Whether to automatically start the agent run timer.")
    start_time: datetime | None = Field(default=None, description="The start time of the agent run.")
    end_time: datetime | None = Field(default=None, description="The end time of the agent run.")

    def mark_start_time(self) -> None:
        """Mark the start time of the agent run.

        This method is automatically called if `auto_start` is True.
        """

        self.start_time = datetime.now(tz=UTC)

    def mark_end_time(self) -> None:
        """Mark the end time of the agent run."""
        self.end_time = datetime.now(tz=UTC)

    @override
    def model_post_init(self, __context: Any) -> None:  # pyright: ignore[reportAny]
        """Post init."""
        if self.auto_start:
            self.mark_start_time()

    @property
    def duration(self) -> timedelta:
        """The duration of the agent run."""

        if self.start_time is None or self.end_time is None:
            msg = "Start or end time is not set."
            raise ValueError(msg)

        return self.end_time - self.start_time

    @property
    def tool_count(self) -> int:
        """The number of tool calls."""
        return len(self.successful_tool_calls) + len(self.failed_tool_calls)

    @property
    def tool_call_summary(self) -> dict[str, int]:
        """The summary of the tool calls."""

        calls: dict[str, int] = {}

        for tool_call in self.successful_tool_calls:
            calls[tool_call] = calls.get(tool_call, 0) + 1

        for tool_call in self.failed_tool_calls:
            calls[tool_call] = calls.get(tool_call, 0) + 1

        return calls
