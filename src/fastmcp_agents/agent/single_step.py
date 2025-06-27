"""Base class for single-step agents."""

import logging
from abc import ABC
from collections.abc import Sequence
from typing import overload

import yaml
from fastmcp import Context
from fastmcp.server.proxy import ProxyTool
from fastmcp.tools import Tool as FastMCPTool
from mcp.types import TextContent
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from fastmcp_agents.conversation.types import (
    AssistantConversationEntry,
    Conversation,
    MCPContent,
    SystemConversationEntry,
    ToolConversationEntry,
    ToolRequestPart,
    UserConversationEntry,
)
from fastmcp_agents.conversation.utils import add_task_to_conversation, build_conversation
from fastmcp_agents.errors.agent import ToolNotFoundError
from fastmcp_agents.llm_link.base import LLMLinkProtocol
from fastmcp_agents.observability.logging import BASE_LOGGER

logger = BASE_LOGGER

SINGLE_STEP_SYSTEM_PROMPT = """
You are a tool calling Agent named `{name}`.

You are described as:
```markdown
{description}
```

You are given instructions and a task and you must perform the task using the tools available to you.
Your tasks may be phrased in the form of `tell {name} to <task>` or just `<task>`.

You are not limited to a single tool call. You may perform many tool calls but you should always
keep in mind that the tool calls may run in any order and may run at the same time.
"""


class BaseAgentModel(BaseModel):
    """A base model for all agents."""

    model_config = ConfigDict(arbitrary_types_allowed=True, use_attribute_docstrings=True)


class SingleStepAgent(BaseAgentModel, ABC):
    """A single-step agent, which can pick tools, calls them or do both in a single step."""

    name: str = Field(...)
    """The name of the agent."""

    description: str = Field(...)
    """The description of the agent."""

    system_prompt: SystemConversationEntry | str = Field(default=SINGLE_STEP_SYSTEM_PROMPT)
    """The system prompt to use."""

    instructions: list[UserConversationEntry] | UserConversationEntry | str = Field(...)
    """The instructions to use."""

    default_tools: list[FastMCPTool] = Field(default_factory=list, exclude=True)
    """The default tools to use."""

    llm_link: LLMLinkProtocol = Field(..., exclude=True)
    """The LLM link to use."""

    logger: logging.Logger = Field(default=BASE_LOGGER, exclude=True)
    """The logger to use."""

    _tool_logger: logging.Logger = PrivateAttr(default=BASE_LOGGER)
    """The logger to use for tool calls."""

    @model_validator(mode="after")
    def _validate_fields(self) -> "SingleStepAgent":
        """Set the loggers."""

        self.logger = BASE_LOGGER.getChild(self.name)
        self._tool_logger = self.logger.getChild("tool")

        return self

    async def call_tool(
        self,
        tool_call_request: ToolRequestPart,
        fastmcp_tool: FastMCPTool,
    ) -> ToolConversationEntry:
        """Run a single tool call request with a single tool."""

        if isinstance(fastmcp_tool, ProxyTool):
            self._tool_logger.info(f"Calling tool {tool_call_request.name} with arguments {tool_call_request.arguments}")

        success = True

        try:
            tool_response: list[MCPContent] = await fastmcp_tool.run(arguments=tool_call_request.arguments)
        except Exception as e:
            tool_response = [TextContent(type="text", text=f"Error calling tool {tool_call_request.name}: {e!s}")]
            success = False

        return ToolConversationEntry.from_tool_request_part(tool_call_request, tool_response, success)

    async def call_tools(
        self,
        tool_call_requests: list[ToolRequestPart],
        fastmcp_tools: Sequence[FastMCPTool] | None = None,
    ) -> list[ToolConversationEntry]:
        """Run a list of tool call requests with a list of tools.

        Args:
            tool_call_requests: The tool call requests to run.
            fastmcp_tools: The tools to use.

        Returns:
            The tool call responses.
        """

        available_tools = fastmcp_tools or self.default_tools

        for tool_call_request in tool_call_requests:
            if tool_call_request.name not in [tool.name for tool in available_tools]:
                raise ToolNotFoundError(self.name, tool_call_request.name)

        self._tool_logger.info(f"Executing {len(tool_call_requests)} tool calls for agent.")

        tool_call_responses = [
            await self.call_tool(tool_call_request, fastmcp_tool)
            for tool_call_request in tool_call_requests
            for fastmcp_tool in available_tools
            if tool_call_request.name == fastmcp_tool.name
        ]

        self._log_call_tools(tool_call_requests, tool_call_responses)

        return tool_call_responses

    def _log_call_tools(self, tool_call_requests: list[ToolRequestPart], conversation_entries: list[ToolConversationEntry]):
        """Log the call tools response."""

        tool_call_yaml = yaml.safe_dump([entry.to_loggable() for entry in conversation_entries], indent=2, sort_keys=False)
        self._tool_logger.info(f"Sharing {len(tool_call_requests)} tool call results:\n{tool_call_yaml}".strip())

    async def pick_tools(
        self,
        conversation: Conversation,
        tools: Sequence[FastMCPTool],
    ) -> AssistantConversationEntry:
        """Send the prompt to the LLM and ask it what tool calls it wants to make.

        Args:
            conversation: The conversation to send to the LLM to solicit tool call requests
            tools: The tools to use.

        Returns:
            A list of CallToolRequest objects.
        """

        assistant_conversation_entry = await self.llm_link.async_completion(conversation=conversation, fastmcp_tools=tools)

        self._log_pick_tools(assistant_conversation_entry)

        return assistant_conversation_entry

    def _log_pick_tools(self, assistant_conversation_entry: AssistantConversationEntry):
        """Log the pick tools response."""

        tool_call_parts = [
            {tool_call_part.name: tool_call_part.arguments} if len(tool_call_part.arguments) > 0 else tool_call_part.name
            for tool_call_part in assistant_conversation_entry.tool_calls
        ]
        tokens = assistant_conversation_entry.token_usage

        tool_call_yaml = yaml.safe_dump(tool_call_parts, indent=2, sort_keys=False)
        self.logger.info(
            f"Needs {len(tool_call_parts)} tool calls ({tokens} tokens):\n{tool_call_yaml}".strip(),
        )

    @overload
    async def run_step(
        self,
        *args,
        ctx: Context,
        task: list[UserConversationEntry] | UserConversationEntry | str,
        tools: list[FastMCPTool] | None = None,
        **kwargs,
    ) -> Conversation:
        """Run a single step of the agent.

        Args:
            ctx: The context of the FastMCP Request.
            task: The task to send to the LLM to solicit tool call requests. Will be merged with the system prompt and instructions.
            tools: The tools to use.

        Returns:
            A conversation with the system prompt, instructions, task, tool call requests and responses.
        """

    @overload
    async def run_step(
        self,
        *args,
        ctx: Context,
        conversation: Conversation,
        task: list[UserConversationEntry] | UserConversationEntry | str | None = None,
        tools: list[FastMCPTool] | None = None,
        **kwargs,
    ) -> Conversation:
        """Run a single step of the agent.

        This method is called to run a single step of the agent. It will:
        - Ask the LLM what tool calls it wants to make
        - Call the tools

        Args:
            ctx: The context of the FastMCP Request.
            conversation: A previous conversation to continue from.
            task: The task to send to the LLM to solicit tool call requests. Will be merged with the system prompt and instructions.
            tools: The tools to use.

        Returns:
            An updated conversation.
        """

    async def run_step(
        self,
        *args,  # noqa: ARG002
        ctx: Context,  # noqa: ARG002
        conversation: Conversation | None = None,
        task: list[UserConversationEntry] | UserConversationEntry | str | None = None,
        tools: Sequence[FastMCPTool] | None = None,
        **kwargs,  # noqa: ARG002
    ) -> Conversation:
        """Run a single step of the agent.

        This method is called to run a single step of the agent. It will:
        - Ask the LLM what tool calls it wants to make
        - Call the tools

        Args:
            ctx: The context of the FastMCP Request.
            tools: The tools to use.
            task: The task to send to the LLM to solicit tool call requests.
            conversation: A previous conversation to continue from.

        Returns:
            A tuple containing the assistant conversation entry with the tool call requests and the tool
            conversation entries with the tool call responses.
        """

        # Use the conversation if provided, otherwise build a new one from the system prompt and instructions.
        new_conversation = self._prepare_conversation(
            conversation=conversation,
            task=task,
        )

        # Pick the Tools
        assistant_conversation_entry = await self.pick_tools(new_conversation, tools or self.default_tools)

        # Call the Tools
        tool_conversation_entries = await self.call_tools(assistant_conversation_entry.tool_calls, tools)

        return new_conversation.extend(
            entries=[assistant_conversation_entry, *tool_conversation_entries],
        )

    def _prepare_conversation(
        self,
        conversation: Conversation | None,
        task: list[UserConversationEntry] | UserConversationEntry | str | None,
    ) -> Conversation:
        """Prepare the conversation for the agent."""

        if conversation is not None:
            return add_task_to_conversation(conversation, task) if task is not None else conversation

        if self.system_prompt is None:
            msg = "system_prompt is required"
            raise ValueError(msg)

        if self.instructions is None:
            msg = "instructions is required"
            raise ValueError(msg)

        system_prompt = (
            self.system_prompt.format(name=self.name, description=self.description)
            if isinstance(self.system_prompt, str)
            else self.system_prompt
        )

        return (
            build_conversation(system_prompt, self.instructions)
            if task is None
            else add_task_to_conversation(build_conversation(system_prompt, self.instructions), task)
        )
