import logging
from abc import ABC

from fastmcp.tools import Tool as FastMCPTool
from mcp.types import EmbeddedResource, ImageContent, TextContent

from fastmcp_agents.conversation.types import (
    CallToolRequest,
    Conversation,
    SystemConversationEntry,
    ToolConversationEntry,
)
from fastmcp_agents.errors.agent import ToolNotFoundError
from fastmcp_agents.llm_link.base import AsyncLLMLink
from fastmcp_agents.observability.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("agent")


class SingleStepAgent(ABC):
    name: str
    description: str
    llm_link: AsyncLLMLink
    default_tools: list[FastMCPTool]
    _logger: logging.Logger
    _tool_logger: logging.Logger
    _system_prompt: Conversation

    def __init__(
        self,
        *,
        name: str,
        description: str,
        system_prompt: str | Conversation,
        default_tools: list[FastMCPTool],
        llm_link: AsyncLLMLink,
    ):
        self.name = name
        self.description = description

        if isinstance(system_prompt, str):
            self._system_prompt = Conversation(entries=[SystemConversationEntry(content=system_prompt)])
        else:
            self._system_prompt = system_prompt

        self.default_tools = default_tools
        self.llm_link = llm_link

        self._logger = logger.getChild(f"{self.name}")
        self._tool_logger = self._logger.getChild("tool_calls")
        self.llm_link.logger = self._logger.getChild("llm_link")

    async def _perform_tool_call_requests(
        self,
        conversation: Conversation,
        requests: list[CallToolRequest],
        tools: list[FastMCPTool],
    ) -> Conversation:
        """Run tool call requests.

        Args:
            conversations: The conversation to add the tool call responses to.
            requests: The tool call requests to run.
            tools: The tools to use. If None, the default tools of the agentwill be used.

        Returns:
            The conversation with the tool call responses added.
        """

        tools_by_name = {tool.name: tool for tool in tools}

        self._tool_logger.info(f"LLM Requests {len(requests)} tool calls: {[request.name for request in requests]}")

        for request in requests:
            tool_name = request.name
            tool_args = request.arguments
            tool_call_id = request.id

            if tool_name not in tools_by_name:
                raise ToolNotFoundError(self.name, tool_name)

            fastmcp_tool = tools_by_name[tool_name]

            self._tool_logger.info(f"Running tool {tool_name} with arguments {tool_args}")

            try:
                tool_response: list[TextContent | ImageContent | EmbeddedResource] = await fastmcp_tool.run(arguments=tool_args)

            # I want any underlying exception to be included in the tool response, even if it's not a ToolError
            # But this should be configurable
            except Exception as e:
                tool_response = [TextContent(type="text", text=f"Error calling tool {tool_name}: {e!s}")]

            self._tool_logger.info(f"Tool {tool_name} returned {len(tool_response)} items: {tool_response[0].text[:100]}...")

            conversation = conversation.add(ToolConversationEntry(tool_call_id=tool_call_id, name=tool_name, content=tool_response))

        return conversation

    async def _generate_tool_call_requests(
        self,
        conversation: Conversation,
        tools: list[FastMCPTool],
    ) -> tuple[Conversation, list[CallToolRequest]]:
        """Send the conversation to the LLM and ask it what tool calls it wants to make.

        Args:
            conversation: The conversation to add the tool call requests to.
            tools: The tools to use. If None, the default tools of the agentwill be used.

        Returns:
            A list of CallToolRequest objects.
        """

        return await self.llm_link.async_completion(
            conversation=conversation,
            tools=[tool.to_mcp_tool() for tool in tools],
        )
