from typing import Generic, Protocol, TypeVar

from fastmcp_agents.conversation.types import Conversation, ConversationEntryTypes


class MemoryProtocol(Protocol):
    """A protocol for memory that can be used to store and retrieve conversation history."""

    def add(self, message: ConversationEntryTypes) -> None: ...

    def get(self) -> list[ConversationEntryTypes]: ...

    def set(self, conversation_history: Conversation) -> None: ...

    def reset(self) -> None: ...

    def persist(self) -> None: ...

    def restore(self) -> None: ...


class EphemeralMemory(MemoryProtocol):
    """A memory entry that is lost when the server restarts"""

    conversation_history: Conversation

    def __init__(self):
        self.conversation_history = Conversation()

    def add(self, message: ConversationEntryTypes):
        self.conversation_history.add(message)

    def get(self):
        return self.conversation_history.get()

    def set(self, conversation_history: Conversation):
        self.conversation_history = conversation_history

    def reset(self) -> None:
        pass

    def persist(self) -> None:
        pass

    def restore(self) -> None:
        pass


MemoryClass = TypeVar("MemoryClass", bound=MemoryProtocol)


class MemoryFactoryProtocol(Protocol):
    """A factory for creating memory instances."""

    def __call__(self) -> MemoryProtocol: ...


class SharedMemoryFactory(MemoryFactoryProtocol, Generic[MemoryClass]):
    """A factory for sharing memory instances."""

    _shared_memory_instance: MemoryClass

    def __init__(self, memory_class: type[MemoryClass] = EphemeralMemory):
        self._memory_class_instance = memory_class()

    def __call__(self) -> MemoryClass:
        return self._memory_class_instance


class PrivateMemoryFactory(MemoryFactoryProtocol, Generic[MemoryClass]):
    """Every call to the PrivateMemoryFactory will return a new memory instance."""

    _memory_class: type[MemoryClass]

    def __init__(self, memory_class: type[MemoryClass] = EphemeralMemory):
        self._memory_class = memory_class

    def __call__(self) -> MemoryClass:
        return self._memory_class()
