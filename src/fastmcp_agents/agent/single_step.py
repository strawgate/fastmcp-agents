"""Base class for single-step agents."""

import logging
from abc import ABC

import yaml
from fastmcp import Context
from fastmcp.tools import Tool as FastMCPTool
from mcp.types import TextContent

from fastmcp_agents.conversation.types import (
    AssistantConversationEntry,
    CallToolRequest,
    CallToolResponse,
    Conversation,
    MCPToolResponseTypes,
    ToolConversationEntry,
    UserConversationEntry,
)
from fastmcp_agents.conversation.utils import join_content
from fastmcp_agents.errors.agent import ToolNotFoundError
from fastmcp_agents.llm_link.base import AsyncLLMLink
from fastmcp_agents.observability.logging import BASE_LOGGER

logger = BASE_LOGGER


class SingleStepAgent(ABC):
    """A single-step agent, which can pick tools, calls them or do both in a single step."""

    name: str
    description: str
    llm_link: AsyncLLMLink
    default_tools: list[FastMCPTool]
    _logger: logging.Logger
    _tool_logger: logging.Logger
    _system_prompt: Conversation

    def __init__(
        self,
        *args,
        name: str,
        description: str,
        llm_link: AsyncLLMLink,
        system_prompt: Conversation,
        default_tools: list[FastMCPTool],
        **kwargs,
    ):
        """Initialize the single-step agent.

        Args:
            name: The name of the agent.
            description: The description of the agent.
            llm_link: The LLM link to use.
            system_prompt: The system prompt to use.
            default_tools: The default tools to use.
        """

        self.name = name
        self.description = description

        self._system_prompt = system_prompt

        self.default_tools = default_tools
        self.llm_link = llm_link

        self._logger = logger.getChild(f"{self.name}")
        self._tool_logger = self._logger.getChild("tool_calls")
        self.llm_link.logger = self._logger.getChild("llm_link")

        super().__init__(*args, **kwargs)

    async def call_tool(
        self,
        tool_call_request: CallToolRequest,
        fastmcp_tool: FastMCPTool,
    ) -> CallToolResponse:
        """Run a single tool call request with a single tool."""

        self._tool_logger.info(f"Calling tool {tool_call_request.name} with arguments {tool_call_request.arguments}")

        try:
            tool_response: list[MCPToolResponseTypes] = await fastmcp_tool.run(arguments=tool_call_request.arguments)
        except Exception as e:
            tool_response = [TextContent(type="text", text=f"Error calling tool {tool_call_request.name}: {e!s}")]

        full_response = join_content(tool_response)
        self._tool_logger.info(f"{tool_call_request.name} returned {len(full_response)} bytes: {str(full_response)[:200]}...")

        return CallToolResponse(
            id=tool_call_request.id,
            name=tool_call_request.name,
            arguments=tool_call_request.arguments,
            content=tool_response,
        )

    async def call_tools(
        self,
        tool_call_requests: list[CallToolRequest],
        fastmcp_tools: list[FastMCPTool],
    ) -> list[CallToolResponse]:
        """Run a list of tool call requests with a list of tools.

        Args:
            tool_call_requests: The tool call requests to run.
            fastmcp_tools: The tools to use.

        Returns:
            The tool call responses.
        """

        for tool_call_request in tool_call_requests:
            if tool_call_request.name not in [tool.name for tool in fastmcp_tools]:
                raise ToolNotFoundError(self.name, tool_call_request.name)

        return [
            await self.call_tool(tool_call_request, fastmcp_tool)
            for tool_call_request in tool_call_requests
            for fastmcp_tool in fastmcp_tools
            if tool_call_request.name == fastmcp_tool.name
        ]

    async def pick_tools(
        self,
        prompt: str | Conversation,
        tools: list[FastMCPTool],
    ) -> AssistantConversationEntry:
        """Send the prompt to the LLM and ask it what tool calls it wants to make.

        Args:
            prompt: The prompt to send to the LLM to solicit tool call requests
            tools: The tools to use.

        Returns:
            A list of CallToolRequest objects.
        """

        if isinstance(prompt, str):
            prompt = self._system_prompt.append(UserConversationEntry(content=prompt))

        assistant_conversation_entry = await self.llm_link.async_completion(conversation=prompt, fastmcp_tools=tools)

        tool_calls = assistant_conversation_entry.tool_calls
        tokens = assistant_conversation_entry.token_usage

        tool_call_yaml = yaml.safe_dump(assistant_conversation_entry.model_dump(exclude_none=True), indent=2, sort_keys=True)
        self._logger.info(f"Agent picked {len(tool_calls)} tool calls ({tokens} tokens): {tool_call_yaml}")

        return assistant_conversation_entry

    async def run_step(
        self,
        *args,  # noqa: ARG002
        ctx: Context,  # noqa: ARG002
        prompt: str | Conversation,
        tools: list[FastMCPTool],
        **kwargs,  # noqa: ARG002
    ) -> tuple[AssistantConversationEntry, list[ToolConversationEntry]]:
        """Run a single step of the agent.

        This method is called to run a single step of the agent. It will:
        - Ask the LLM what tool calls it wants to make
        - Call the tools

        Args:
            ctx: The context of the FastMCP Request.
            prompt: The prompt to send to the LLM to solicit tool call requests
            tools: The tools to use.

        Returns:
            A tuple containing the assistant conversation entry with the tool call requests and the tool
            conversation entries with the tool call responses.
        """

        if isinstance(prompt, str):
            prompt = self._system_prompt.append(UserConversationEntry(content=prompt))

        assistant_conversation_entry = await self.pick_tools(prompt, tools)

        return assistant_conversation_entry, [
            ToolConversationEntry.from_tool_call_response(tool_call_response)
            for tool_call_response in await self.call_tools(assistant_conversation_entry.tool_calls, tools)
        ]
