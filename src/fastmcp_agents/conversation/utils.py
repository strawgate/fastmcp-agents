"""Utility functions for conversation handling."""

from collections.abc import Sequence

from mcp.types import BlobResourceContents, EmbeddedResource, ImageContent, TextContent, TextResourceContents

from fastmcp_agents.conversation.types import (
    AssistantConversationEntry,
    Conversation,
    SystemConversationEntry,
    ToolConversationEntry,
    UserConversationEntry,
)


def join_content(content: list[TextContent | ImageContent | EmbeddedResource]) -> str:
    """Join the content of a list of TextContent, ImageContent, or EmbeddedResource into a single string.

    Args:
        content: The list of content to join.

    Returns:
        A string of the joined content.
    """

    result = ""

    for item in content:
        if isinstance(item, TextContent):
            result += item.text
        elif isinstance(item, ImageContent):
            result += f"an image {item.mimeType}"
        elif isinstance(item, BlobResourceContents):
            result += f"a blob {item.mimeType}"
        elif isinstance(item, TextResourceContents):
            result += f"a text resource {item.text}"
        elif isinstance(item, EmbeddedResource):
            result += f"an embedded resource {item.type}"

    return result


def build_conversation(
    system_prompt: SystemConversationEntry | str,
    instructions: Sequence[AssistantConversationEntry | UserConversationEntry] | UserConversationEntry | str | None,
) -> Conversation:
    """Prepare the conversation for the agent. Either by using the conversation history or the instructions."""

    new_conversation: Conversation = Conversation()

    if isinstance(system_prompt, str):
        new_conversation = new_conversation.append(SystemConversationEntry(content=system_prompt))
    else:
        new_conversation.append(system_prompt)

    if instructions is not None:
        if isinstance(instructions, str):
            new_conversation = new_conversation.append(UserConversationEntry(content=instructions))
        elif isinstance(instructions, UserConversationEntry):
            new_conversation = new_conversation.append(instructions)
        else:
            new_conversation = new_conversation.extend(instructions)

    return new_conversation


def add_task_to_conversation(
    conversation: Conversation,
    task: list[UserConversationEntry] | UserConversationEntry | str,
) -> Conversation:
    """Add a task to the conversation."""

    if isinstance(task, str):
        conversation = conversation.append(UserConversationEntry(content=task))
    elif isinstance(task, UserConversationEntry):
        conversation = conversation.append(task)
    else:
        conversation = conversation.extend(task)

    return conversation


def prepare_conversation(
    conversation: Conversation | None,
    system_prompt: SystemConversationEntry | str | None,
    instructions: Sequence[AssistantConversationEntry | UserConversationEntry] | UserConversationEntry | str | None,
    task: list[UserConversationEntry] | UserConversationEntry | str | None,
) -> Conversation:
    """Prepare the conversation for the agent."""

    if conversation is not None:
        return add_task_to_conversation(conversation, task) if task is not None else conversation

    if system_prompt is None:
        msg = "system_prompt is required"
        raise ValueError(msg)

    if instructions is None:
        msg = "instructions is required"
        raise ValueError(msg)

    return (
        build_conversation(system_prompt, instructions)
        if task is None
        else add_task_to_conversation(build_conversation(system_prompt, instructions), task)
    )


def get_tool_calls_from_conversation(conversation: Conversation) -> list[ToolConversationEntry]:
    """Get the tool calls from the conversation."""

    return [entry for entry in conversation.entries if isinstance(entry, ToolConversationEntry)]
