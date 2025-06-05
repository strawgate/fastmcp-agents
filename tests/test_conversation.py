import pytest

from fastmcp_agents.conversation.types import (
    AssistantConversationEntry,
    CallToolRequest,
    Conversation,
    SystemConversationEntry,
    TextContent,
    ToolConversationEntry,
    UserConversationEntry,
)


@pytest.fixture
def conversation():
    """Create a fresh conversation for each test."""
    return Conversation()


def test_conversation_initialization(conversation: Conversation):
    """Test that a conversation can be initialized."""
    assert conversation is not None
    assert len(conversation.entries) == 0


def test_conversation_add_system_message():
    """Test adding a system message to the conversation."""
    conv: Conversation = Conversation()
    system_entry = SystemConversationEntry(content="You are a test assistant")
    new_conv = conv.append(system_entry)

    assert len(new_conv.entries) == 1
    assert new_conv.entries[0].role == "system"
    assert new_conv.entries[0].content == "You are a test assistant"


def test_conversation_add_user_message():
    """Test adding a user message to the conversation."""
    conv: Conversation = Conversation()
    user_entry = UserConversationEntry(content="Hello")
    new_conv = conv.append(user_entry)

    assert len(new_conv.entries) == 1
    assert new_conv.entries[0].role == "user"
    assert new_conv.entries[0].content == "Hello"


def test_conversation_add_assistant_message_with_tool_calls():
    """Test adding an assistant message with tool calls."""
    conv: Conversation = Conversation()
    tool_calls = [CallToolRequest(id="call_1", name="test_tool", arguments={"param": "value"})]
    assistant_entry = AssistantConversationEntry(content="I'll help you with that", tool_calls=tool_calls)
    new_conv = conv.append(assistant_entry)

    assert len(new_conv.entries) == 1
    assert new_conv.entries[0].role == "assistant"
    assert new_conv.entries[0].content == "I'll help you with that"
    assert len(new_conv.entries[0].tool_calls) == 1
    assert new_conv.entries[0].tool_calls[0].name == "test_tool"


def test_conversation_add_tool_response():
    """Test adding a tool response to the conversation."""
    conv: Conversation = Conversation()
    tool_entry = ToolConversationEntry(tool_call_id="call_1", name="test_tool", content=[TextContent(type="text", text="Tool response")])
    new_conv = conv.append(tool_entry)

    assert len(new_conv.entries) == 1
    assert new_conv.entries[0].role == "tool"
    assert new_conv.entries[0].tool_call_id == "call_1"
    assert new_conv.entries[0].name == "test_tool"
    assert isinstance(new_conv.entries[0].content[0], TextContent)


def test_conversation_merge():
    """Test merging multiple conversations."""
    conv1 = Conversation().append(SystemConversationEntry(content="System message"))
    conv2 = Conversation().append(UserConversationEntry(content="User message"))

    merged = conv1.merge(conv2)
    assert len(merged.entries) == 2
    assert merged.entries[0].role == "system"
    assert merged.entries[1].role == "user"


def test_conversation_to_messages():
    """Test converting conversation to message format."""
    conv: Conversation = Conversation()
    conv = conv.append(SystemConversationEntry(content="System message"))
    conv = conv.append(UserConversationEntry(content="User message"))

    messages = conv.to_messages()
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_get_messages(conversation: Conversation):
    """Test retrieving messages from the conversation."""

    # Conversation is immutable, so we need to add to a new conversation
    conversation = conversation.append(UserConversationEntry(content="Hello"))
    conversation = conversation.append(AssistantConversationEntry(content="Hi there!"))

    messages = conversation.get()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[0].content == "Hello"
    assert messages[1].content == "Hi there!"
