"""Ephemeral memory implementation."""

from fastmcp_agents.conversation.memory.base import MemoryProtocol
from fastmcp_agents.conversation.types import Conversation, ConversationEntryTypes


class EphemeralMemory(MemoryProtocol):
    """A memory entry that is lost when the server restarts"""

    conversation_history: Conversation

    def __init__(self):
        self.conversation_history = Conversation()

    def add(self, message: ConversationEntryTypes):
        self.conversation_history.append(message)

    def get(self) -> Conversation:
        return self.conversation_history

    def set(self, conversation_history: Conversation):
        self.conversation_history = conversation_history

    def reset(self) -> None:
        pass

    def persist(self) -> None:
        pass

    def restore(self) -> None:
        pass
