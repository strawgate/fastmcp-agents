from typing import Generic, Protocol, TypeVar

from fastmcp_agents.conversation.memory.base import EphemeralMemory, MemoryProtocol


class MemoryFactory(Protocol):
    """A factory for creating memory instances."""

    def create(self, agent_name: str) -> MemoryProtocol: ...


MemoryClass = TypeVar("MemoryClass", bound=MemoryProtocol)


class SharedMemoryFactory(Generic[MemoryClass]):
    """A factory for sharing memory instances."""

    _shared_memory_instance: MemoryClass

    def __init__(self, memory_class: type[MemoryClass] = EphemeralMemory):
        self._memory_class_instance = memory_class()

    def __call__(self) -> MemoryClass:
        return self._memory_class_instance


class PrivateMemoryFactory(Generic[MemoryClass]):
    """Every call to the PrivateMemoryFactory will return a new memory instance."""

    _memory_class: type[MemoryClass]

    def __init__(self, memory_class: type[MemoryClass] = EphemeralMemory):
        self._memory_class = memory_class

    def __call__(self) -> MemoryClass:
        return self._memory_class()
