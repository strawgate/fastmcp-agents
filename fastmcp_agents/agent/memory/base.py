from typing import Protocol

from pydantic import BaseModel, Field

from fastmcp_agents.agent.types import ConversationEntryTypes


class ConversationHistory(BaseModel):
    entries: list[ConversationEntryTypes] = Field(default_factory=list[ConversationEntryTypes])

    def add(self, message: ConversationEntryTypes) -> None:
        self.entries.append(message)

    def get(self) -> list[ConversationEntryTypes]:
        return self.entries
    
    def set(self, entries: list[ConversationEntryTypes]) -> None:
        self.entries = entries


class MemoryProtocol(Protocol):
    def add(self, message: ConversationEntryTypes) -> None: ...

    def get(self) -> list[ConversationEntryTypes]: ...

    def reset(self) -> None: ...

    def persist(self) -> None: ...

    def restore(self) -> None: ...
