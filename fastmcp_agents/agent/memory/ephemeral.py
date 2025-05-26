from pydantic import Field

from fastmcp_agents.agent.memory.base import ConversationHistory, MemoryProtocol
from fastmcp_agents.agent.types import ConversationEntryTypes


class EphemeralMemory(MemoryProtocol):
    conversation_history: ConversationHistory

    def __init__(self):
        self.conversation_history = ConversationHistory()

    def add(self, message: ConversationEntryTypes):
        self.conversation_history.add(message)

    def get(self):
        return self.conversation_history.get()

    def set(self, conversation_history: ConversationHistory):
        self.conversation_history = conversation_history

    def reset(self) -> None:
        self.conversation_history = ConversationHistory()

    def persist(self) -> None:
        pass

    def restore(self) -> None:
        pass
