from typing import Generic, Protocol, TypeVar

from fastmcp_agents.conversation.types import Conversation, ConversationEntryTypes


class MemoryProtocol(Protocol):
    """A protocol for memory that can be used to store and retrieve conversation history."""

    def add(self, message: ConversationEntryTypes) -> None: ...

    def get(self) -> Conversation: ...

    def set(self, conversation_history: Conversation) -> None: ...

    def reset(self) -> None: ...

    def persist(self) -> None: ...

    def restore(self) -> None: ...


MemoryClass = TypeVar("MemoryClass", bound=MemoryProtocol)


class MemoryFactoryProtocol(Protocol):
    """A factory for creating memory instances."""

    def __call__(self) -> MemoryProtocol: ...


class SharedMemoryFactory(MemoryFactoryProtocol, Generic[MemoryClass]):
    """A factory for sharing memory instances."""

    _shared_memory_instance: MemoryClass

    def __init__(self, memory_class: type[MemoryClass]):
        self._memory_class_instance = memory_class()

    def __call__(self) -> MemoryClass:
        return self._memory_class_instance


class PrivateMemoryFactory(MemoryFactoryProtocol, Generic[MemoryClass]):
    """Every call to the PrivateMemoryFactory will return a new memory instance."""

    _memory_class: type[MemoryClass]

    def __init__(self, memory_class: type[MemoryClass]):
        self._memory_class = memory_class

    def __call__(self) -> MemoryClass:
        return self._memory_class()
