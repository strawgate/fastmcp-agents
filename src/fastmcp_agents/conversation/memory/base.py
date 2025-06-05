"""Base classes and protocols for memory."""

from typing import Generic, Protocol, TypeVar

from fastmcp_agents.conversation.types import Conversation, ConversationEntryTypes


class MemoryProtocol(Protocol):
    """A protocol for memory that can be used to store and retrieve conversation history."""

    def add(self, message: ConversationEntryTypes) -> None: ...

    """Add a message to the conversation history."""

    def get(self) -> Conversation: ...

    """Get the current conversation history."""

    def set(self, conversation_history: Conversation) -> None: ...

    """Set the current conversation history."""

    def reset(self) -> None: ...

    """Reset the memory."""

    def persist(self) -> None: ...

    """Persist the memory."""

    def restore(self) -> None: ...

    """Restore the memory."""


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
        """Return the shared memory instance."""
        return self._memory_class_instance


class PrivateMemoryFactory(MemoryFactoryProtocol, Generic[MemoryClass]):
    """Every call to the PrivateMemoryFactory will return a new memory instance."""

    _memory_class: type[MemoryClass]

    def __init__(self, memory_class: type[MemoryClass]):
        self._memory_class = memory_class

    def __call__(self) -> MemoryClass:
        """Return a new memory instance."""
        return self._memory_class()
