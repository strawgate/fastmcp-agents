"""Models and methods for conversation handling."""

from collections.abc import Sequence
from typing import Literal, TypedDict

from fastmcp_agents.core.completions.base import CompletionMessageType


class Message(TypedDict):
    """A message in a conversation."""

    content: str


class SystemMessage(Message):
    """A system message in a conversation."""

    role: Literal["system"]


class UserMessage(Message):
    """A user message in a conversation."""

    role: Literal["user"]


def initial_messages(
    system_prompt: str | None = None,
    instructions: list[str] | str | None = None,
    messages: Sequence[CompletionMessageType] | None = None,
) -> list[CompletionMessageType]:
    """Get the initial messages for a conversation."""
    all_messages: list[CompletionMessageType] = []

    if system_prompt:
        all_messages.append(SystemMessage(role="system", content=system_prompt))

    if instructions:
        if isinstance(instructions, str):
            all_messages.append(UserMessage(role="user", content=instructions))
        else:
            all_messages.extend(UserMessage(role="user", content=instruction) for instruction in instructions)

    if messages:
        all_messages.extend(messages)

    return all_messages


# class ConversationBuilder(BaseConvoModel):
#     """A builder for conversations."""

#     _system_entry: CompletionMessageType | None = PrivateAttr(default=None)
#     """The system entry for the conversation."""

#     _instructions_entry: CompletionMessageType | None = PrivateAttr(default=None)
#     """The initial instructions entry for the conversation."""

#     _task_entry: CompletionMessageType | None = PrivateAttr(default=None)
#     """The task entry for the conversation."""

#     _other_entries: list[CompletionMessageType] = PrivateAttr(default_factory=list)
#     """The conversation entries."""

#     def __init__(
#         self,
#         task: str | None = None,
#         *,
#         conversation: Conversation | None = None,
#         system_prompt: str | None = None,
#         instructions: list[str] | str | None = None,
#     ):
#         """Initialize the conversation builder."""

#         if not any((conversation, system_prompt, instructions, task)):
#             msg = "At least one of conversation, system_prompt, instructions, or task must be provided."
#             raise ValueError(msg)

#         if conversation is not None and any((system_prompt, instructions)):
#             msg = "Cannot provide both conversation and system_prompt or instructions."
#             raise ValueError(msg)

#         if conversation:
#             _ = self.from_conversation(conversation)

#         if system_prompt:
#             _ = self.system_prompt(system_prompt)

#         if instructions:
#             _ = self.instructions(instructions)

#         if task:
#             _ = self.task(task)

#         super().__init__()

#     @classmethod
#     def from_sampling_messages(cls, messages: str | list[str | SamplingMessage]) -> "ConversationBuilder":
#         if isinstance(messages, str):
#             return cls(task=messages)

#         conversation: Conversation = []

#         for message in messages:
#             if isinstance(message, str):
#                 conversation.append(ChatCompletionUserMessageParam(role="user", content=message))
#                 continue

#             if not isinstance(message.content, TextContent):
#                 msg = "Only Text sampling messages are supported."
#                 raise NotImplementedError

#             if message.role == "user":
#                 conversation.append(ChatCompletionUserMessageParam(role="user", content=message.content.text))
#                 continue

#             if message.role == "assistant":
#                 conversation.append(ChatCompletionAssistantMessageParam(role="assistant", content=message.content.text))
#                 continue

#             msg = f"Unsupported message role: {message.role}"
#             raise ValueError(msg)

#         return cls(conversation=conversation)

#     @classmethod
#     def from_conversation(cls, conversation: Sequence[OpenAIMessageTypes]) -> "ConversationBuilder":
#         """Create a conversation builder from a list of entries."""
#         builder = cls()

#         for i, entry in enumerate(conversation):
#             if i == 0 and entry["role"] == "system":
#                 builder._system_entry = entry
#                 continue

#             if i == 1 and entry["role"] == "user":
#                 builder._instructions_entry = entry
#                 continue

#             if i == 2 and entry["role"] == "user":
#                 builder._task_entry = entry
#                 continue

#             builder._other_entries.append(entry)

#         return builder

#     @property
#     def entries_without_system_prompt(self) -> Sequence[OpenAIMessageTypes]:
#         """Get the conversation entries without the system prompt."""
#         entries: Sequence[OpenAIMessageTypes] = []

#         if self._system_entry:
#             entries.append(self._system_entry)

#         if self._instructions_entry:
#             entries.append(self._instructions_entry)

#         if self._task_entry:
#             entries.append(self._task_entry)

#         entries.extend(self._other_entries)

#         return entries

#     @property
#     def entries(self) -> Sequence[OpenAIMessageTypes]:
#         """Get the conversation entries."""
#         entries: Sequence[OpenAIMessageTypes] = []

#         if self._system_entry:
#             entries.append(self._system_entry)

#         entries.extend(self.entries_without_system_prompt)

#         return entries

#     @property
#     def pending_tool_requests(self) -> list[ChatCompletionMessageToolCallParam]:
#         """Get the pending tool requests from the most recent assistant message."""

#         if not (assistant_message := self._other_entries[-1]) or assistant_message["role"] != "assistant":
#             return []

#         return list(assistant_message.get("tool_calls", []))

#     def system_prompt(self, system_prompt: str | None = None) -> "ConversationBuilder":
#         """Set the system prompt for the conversation."""

#         if system_prompt is None:
#             self._system_entry = None
#         else:
#             self._system_entry = ChatCompletionSystemMessageParam(role="system", content=system_prompt)

#         return self

#     def instructions(self, instructions: list[str] | str | None = None) -> "ConversationBuilder":
#         """Set the instructions for the conversation."""
#         if instructions is None:
#             self._instructions_entry = None
#         else:
#             self._instructions_entry = ChatCompletionUserMessageParam(
#                 role="user", content="\n".join(instructions) if isinstance(instructions, list) else instructions
#             )

#         return self

#     def task(self, task: str | None = None) -> "ConversationBuilder":
#         """Set the task for the conversation."""
#         if task is None:
#             self._task_entry = None
#         else:
#             self._task_entry = ChatCompletionUserMessageParam(role="user", content=task)

#         return self

#     def append(self, entry: OpenAIMessageTypes) -> "ConversationBuilder":
#         """Append an entry to the conversation."""
#         self._other_entries.append(entry)
#         return self

#     def extend(self, entries: Sequence[CompletionMessageType]) -> "ConversationBuilder":
#         """Extend the conversation with the given entries."""

#         for entry in entries:
#             self._other_entries.append(self.type_adapter.validate_python(entry))
#         return self

#     def assistant(self, content: str) -> "ConversationBuilder":
#         """Add a followup entry to the conversation."""
#         self._other_entries.append(ChatCompletionAssistantMessageParam(role="assistant", content=content))

#         return self

#     def user(self, content: str) -> "ConversationBuilder":
#         """Add a user entry to the conversation."""
#         self._other_entries.append(ChatCompletionUserMessageParam(role="user", content=content))
#         return self

# def sampling(self, message: SamplingMessage) -> "ConversationBuilder":
#     """Add a sampling message to the conversation."""
#     if not isinstance(message.content, TextContent):
#         msg = f"Unsupported content type: {type(message.content)}"
#         raise TypeError(msg)

#     if message.role == "user":
#         self._instructions_entry = ChatCompletionUserMessageParam(role="user", content=message.content.text)
#         return self

#     self._other_entries.append(ChatCompletionAssistantMessageParam(role="assistant", content=message.content.text))
#     return self

# def tool_response(self, tool_call_id: str, content: list[ContentBlock]) -> "ConversationBuilder":
#     """Add a tool entry to the conversation."""
#     content_parts: list[ChatCompletionContentPartTextParam] = []

#     for block in content:
#         if isinstance(block, TextContent):
#             content_parts.append(ChatCompletionContentPartTextParam(type="text", text=block.text))
#         # elif isinstance(block, ImageContent):
#         #     content_parts.append(ChatCompletionContentPartImageParam(type="image_url", image_url=ImageURL(url=block.data)))
#         # elif isinstance(block, AudioContent):
#         #     content_parts.append(
#         #         ChatCompletionContentPartInputAudioParam(type="input_audio", input_audio=InputAudio(data=block.data, format="wav"))
#         #     )
#         else:
#             msg = f"Unsupported content block type: {type(block)}"
#             raise TypeError(msg)

#     new_tool_entry: ChatCompletionToolMessageParam = ChatCompletionToolMessageParam(
#         role="tool", content=content_parts, tool_call_id=tool_call_id
#     )

#     self._other_entries.append(new_tool_entry)
#     return self


# def convert_assistant_message(
#     message: ChatCompletionAssistantMessageParam,
#     *,
#     convert_to: type[AssistantMessageConvertToTypes],
#     conversation: Conversation | None = None,
# ) -> AssistantMessageConvertToTypes:
#     """Convert an assistant message to a conversation."""

#     if convert_to is Conversation:
#         if conversation:
#             conversation.append(message)
#         return cast("AssistantMessageConvertToTypes", conversation)

#     if convert_to is ChatCompletionAssistantMessageParam:
#         return cast("AssistantMessageConvertToTypes", message)

#     if convert_to is list[TextContent]:
#         return cast("AssistantMessageConvertToTypes", convert_assistant_message_to_text_contents(message))

#     if convert_to is TextContent:
#         return cast("AssistantMessageConvertToTypes", convert_assistant_message_to_text_content(message))

#     if convert_to is list[str]:
#         return cast("AssistantMessageConvertToTypes", convert_assistant_entry_to_str_list(message))

#     return cast("AssistantMessageConvertToTypes", convert_assistant_entry_to_str(message))


# def convert_assistant_message_to_text_contents(message: ChatCompletionAssistantMessageParam) -> list[TextContent]:
#     """Convert an assistant message to a text content."""

#     return [TextContent(type="text", text=text) for text in convert_assistant_entry_to_str_list(message)]


# def convert_assistant_message_to_text_content(message: ChatCompletionAssistantMessageParam) -> TextContent:
#     """Convert an assistant message to a text content."""
#     return TextContent(type="text", text=convert_assistant_entry_to_str(message))


# def convert_assistant_entry_to_str(assistant_entry: ChatCompletionAssistantMessageParam) -> str:
#     """Convert an assistant entry to a string."""
#     return "\n".join(convert_assistant_entry_to_str_list(assistant_entry))


# def convert_assistant_entry_to_str_list(assistant_entry: ChatCompletionAssistantMessageParam) -> list[str]:
#     """Convert an assistant entry to a string."""

#     if content_value := assistant_entry.get("content"):
#         if isinstance(content_value, str):
#             return [content_value]

#         content_parts: list[ContentArrayOfContentPart] = list(content_value)

#         text_contents: list[str] = [content_part["text"] for content_part in content_parts if content_part["type"] == "text"]

#         return text_contents

#     msg = "The assistant entry is None."
#     raise ValueError(msg)


# def convert_fastmcp_tool_to_openai_tool_param_message(fastmcp_tool: FastMCPTool) -> ChatCompletionToolParam:
#     """Convert an FastMCP tool to an OpenAI tool."""

#     tool_name = fastmcp_tool.name
#     tool_description = fastmcp_tool.description or ""
#     tool_parameters = deepcopy(fastmcp_tool.parameters)

#     return ChatCompletionToolParam(
#         type="function",
#         function=FunctionDefinition(
#             name=tool_name,
#             description=tool_description,
#             parameters=tool_parameters,
#             strict=False,
#         ),
#     )
