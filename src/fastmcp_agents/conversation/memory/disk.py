"""Disk-backed memory implementation."""

from pathlib import Path

import yaml
from pydantic import Field

from fastmcp_agents.conversation.memory.base import Conversation, MemoryProtocol
from fastmcp_agents.conversation.types import ConversationEntryTypes
from fastmcp_agents.errors.base import ContributionsWelcomeError


class DiskBackedMemory(MemoryProtocol):
    """
    A memory entry that is backed by a disk file.

    NOTE: This feature is currently unimplemented. Contributions are welcome!
    """

    conversation_history: Conversation = Field(default_factory=Conversation)
    path: Path

    def __init__(self, path: Path | str):
        """
        Initializes the DiskBackedMemory.

        Args:
            path: The path to the file to store the conversation history.

        Raises:
            ContributionsWelcomeError: This feature is currently unimplemented.
        """
        raise ContributionsWelcomeError(feature="DiskBackedMemory")
        self.path = Path(path)

        if self.path.exists():
            self.restore()
        else:
            self.conversation_history = Conversation()

    def add(self, message: ConversationEntryTypes):
        self.conversation_history.append(message)

    def get(self):
        return self.conversation_history.get()

    def reset(self) -> None:
        pass

    def persist(self) -> None:
        with self.path.open("w") as f:
            conversation_history_dict = [conversation_entry.model_dump() for conversation_entry in self.conversation_history.get()]

            yaml.safe_dump(conversation_history_dict, f, width=140)

    def restore(self):
        with self.path.open("r") as f:
            conversation_history_dict = yaml.safe_load(f)

            self.conversation_history = Conversation.model_validate(**conversation_history_dict)
