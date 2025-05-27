import logging
from abc import ABC
from collections.abc import Callable
from typing import Any, Literal, TypeVar

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import Tool as FastMCPTool
from mcp import Tool as MCPTool
from mcp.types import EmbeddedResource, ImageContent, TextContent
from pydantic import BaseModel, PrivateAttr, computed_field

from fastmcp_agents.agent.errors.agent import NoResponseError, TaskFailureError, ToolNotFoundError
from fastmcp_agents.agent.llm_link.base import AsyncLLMLink
from fastmcp_agents.agent.memory.base import MemoryProtocol
from fastmcp_agents.agent.memory.ephemeral import EphemeralMemory
from fastmcp_agents.agent.observability.logging import BASE_LOGGER
from fastmcp_agents.agent.types import (
    ConversationEntryTypes,
    DefaultErrorResponseModel,
    DefaultSuccessResponseModel,
    SystemConversationEntry,
    ToolCallChatEntry,
    UserConversationEntry,
)

_DEFAULT_SEPARATOR_TOOL = "_"
_DEFAULT_SEPARATOR_RESOURCE = "+"
_DEFAULT_SEPARATOR_PROMPT = "_"

STEP_LIMIT = 10

SUCCESS_RESPONSE_MODEL = TypeVar("SUCCESS_RESPONSE_MODEL", bound=BaseModel)
ERROR_RESPONSE_MODEL = TypeVar("ERROR_RESPONSE_MODEL", bound=BaseModel)

REQUEST_MODEL = TypeVar("REQUEST_MODEL", bound=BaseModel)


_MCP_REGISTRATION_TOOL_ATTR = "_mcp_agent_tool_registration"

DEFAULT_SYSTEM_PROMPT = """
You are `{agent_name}`, an AI Agent that is embedded into a FastMCP Server. You act as an interface between the remote user/agent
and the tools available on the server.

The person or Agent that invoked you understood that you:

````````markdown
{agent_description}
````````

When you are asked to perform a task, you should leverage the tools available to you to perform the task. You may perform many tool calls in one
go but you should always keep in mind that the tool calls may run in any order and will run at the same time. So you should plan for which calls
you can do in parallel (multiple in a single request) and which calls you should do sequentially (one tool call per call).

````````markdown
{default_instructions}
````````

When you have successfully completed the task, you can report task success by calling the `report_task_success` tool and providing
the required information for that tool. When you do report task success, it must be the sole tool call in the response.

If you are unable to complete the task, you can report task failure by calling the `report_task_failure` tool and providing the
required information for that tool. When you do report task failure, it must be the sole tool call in the response.
"""


def agent_tool(
    name: str | None = None,
    description: str | None = None,
    tags: set[str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to mark a method as an MCP tool for later registration."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        call_args = {
            "name": name or func.__name__,
            "description": description,
            "tags": tags,
        }
        call_args = {k: v for k, v in call_args.items() if v is not None}
        setattr(func, _MCP_REGISTRATION_TOOL_ATTR, call_args)
        return func

    return decorator


class BaseFastMCPAgent(ABC):
    name: str
    description: str
    system_prompt: str
    llm_link: AsyncLLMLink
    tools: list[FastMCPTool]
    tool_choice: Literal["auto", "required", "none"]
    memory: MemoryProtocol
    _logger: logging.Logger = PrivateAttr()

    def __init__(
        self,
        *,
        name: str,
        description: str,
        llm_link: AsyncLLMLink,
        tools: list[FastMCPTool],
        memory: MemoryProtocol | None = None,
        # tool_choice: Literal["auto", "required", "none"],
        default_instructions: str | None = None,
    ):
        self.name = name
        self.description = description
        self.system_prompt = DEFAULT_SYSTEM_PROMPT.format(
            agent_name=name,
            agent_description=description,
            default_instructions=default_instructions,
        )
        self.llm_link = llm_link
        self.tools = tools
        self.memory = memory or EphemeralMemory()
        self.tool_choice = "required"

        self._logger = BASE_LOGGER.getChild("agent").getChild(f"{self.name}")

        self.llm_link.logger = self._logger.getChild("llm_link")

    @computed_field
    def tool_names(self) -> list[str]:
        return [tool.name for tool in self.tools]

    def _has_method_to_register(self, registration_type: str):
        return any(
            hasattr(getattr(self, method_name), registration_type) for method_name in dir(self) if callable(getattr(self, method_name))
        )

    def _get_methods_to_register(self, registration_type: str):
        """Retrieves all methods marked for a specific registration type."""
        return [
            (
                getattr(self, method_name),
                getattr(getattr(self, method_name), registration_type).copy(),
            )
            for method_name in dir(self)
            if callable(getattr(self, method_name)) and hasattr(getattr(self, method_name), registration_type)
        ]

    def register_as_tools(
        self,
        server: FastMCP,
        prefix: str | None = None,
        separator: str = _DEFAULT_SEPARATOR_TOOL,
    ):  # Here we either:
        # 1. Enable a direct call to the model with instructions
        # 2. Enable methods on the agent to be registered as tools
        if not self._has_method_to_register(_MCP_REGISTRATION_TOOL_ATTR):

            async def call_with_default_response_model(ctx: Context, instructions: str) -> DefaultSuccessResponseModel:
                return await self.run_async(
                    ctx,
                    instructions,
                    success_response_model=DefaultSuccessResponseModel,
                    error_response_model=DefaultErrorResponseModel,
                )

            server.add_tool(
                fn=call_with_default_response_model,
                name=self.name,
                description=self.description,
            )

        for method, registration_info in self._get_methods_to_register(_MCP_REGISTRATION_TOOL_ATTR):
            if prefix:
                registration_info["name"] = f"{prefix}{separator}{registration_info['name']}"
            server.add_tool(fn=method, **registration_info)

    def as_tools(self) -> list[FastMCPTool]:
        return [
            FastMCPTool.from_function(
                fn=method,
                name=registration_info["name"],
                description=registration_info["description"],
            )
            for method, registration_info in self._get_methods_to_register(_MCP_REGISTRATION_TOOL_ATTR)
        ]

    async def _pre_tool_call(self, ctx: Context, tool_name: str, tool_parameters: dict[str, Any]) -> None:
        # TODO: Telemetry?
        self._logger.info(f"Calling tool: {tool_name} with parameters: {tool_parameters}")

    async def _handle_tool_call(
        self, ctx: Context, tool_name: str, tool_parameters: dict[str, Any]
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        await self._pre_tool_call(ctx, tool_name, tool_parameters)

        tools_by_name = {tool.name: tool for tool in self.tools}

        tool_to_call = tools_by_name.get(tool_name)

        if not tool_to_call:
            raise ToolNotFoundError(self.name, tool_name)

        try:
            tool_response: list[TextContent | ImageContent | EmbeddedResource] = await tool_to_call.run(arguments=tool_parameters)
        except Exception as e:
            tool_response = [TextContent(type="text", text=f"Error calling tool {tool_name}: {e!s}")]

        await self._post_tool_call(ctx, tool_name, tool_parameters, tool_response)

        return tool_response

    @classmethod
    def _tool_call_to_chat_entry(
        cls, tool_call_id: str, tool_name: str, response: list[TextContent | ImageContent | EmbeddedResource]
    ) -> ToolCallChatEntry:
        return ToolCallChatEntry(role="tool", tool_call_id=tool_call_id, name=tool_name, content=response)

    async def _post_tool_call(
        self,
        ctx: Context,
        tool_name: str,
        tool_parameters: dict[str, Any],
        tool_response: Any,
    ) -> None:
        # TODO: Telemetry?
        self._logger.debug({"tool_name": tool_name, "tool_parameters": tool_parameters, "tool_response": tool_response})

    async def _run_step_async(
        self,
        ctx: Context,
        messages: list[ConversationEntryTypes],
        tools: list[MCPTool],
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
    ) -> SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL | None:

        assistant_conversation_entry, tool_call_requests = await self.llm_link.async_completion(
            messages=[message.model_dump() for message in messages],
            tools=tools,
        )

        self.memory.add(assistant_conversation_entry)

        tool_call_request_names = [tool_call_request.name for tool_call_request in tool_call_requests]

        self._logger.info(f"Requested {len(tool_call_requests)} tool calls: {tool_call_request_names}")

        if len(tool_call_requests) >= 5:
            self._logger.warning(f"Requested {len(tool_call_requests)} tool calls, which is more than the maximum of 5")

        for tool_call_request in tool_call_requests:
            tool_name = tool_call_request.name
            tool_args = tool_call_request.arguments
            tool_call_id = tool_call_request.id

            if tool_name == "report_task_success":
                return success_response_model.model_validate(tool_args)

            if tool_name == "report_task_failure":
                return error_response_model.model_validate(tool_args)

            tool_response: list[TextContent | ImageContent | EmbeddedResource] = await self._handle_tool_call(ctx, tool_name, tool_args)

            chat_entry = self._tool_call_to_chat_entry(tool_call_id=tool_call_id, tool_name=tool_name, response=tool_response)

            self.memory.add(chat_entry)

        return None

    @classmethod
    def _completion_tools(
        cls,
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
    ) -> list[MCPTool]:
        report_success = MCPTool(
            name="report_task_success",
            inputSchema=success_response_model.model_json_schema(),
            description="Report successful completion of the task.",
        )
        report_error = MCPTool(
            name="report_task_failure",
            inputSchema=error_response_model.model_json_schema(),
        )

        return [report_success, report_error]

    # async def _run_planning_step_async(self, ctx: Context, messages: list[ConversationEntryTypes], tools: list[MCPTool]) -> PLANNING_RESPONSE:

    async def run_async(
        self,
        ctx: Context,
        instructions: str,
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
    ) -> SUCCESS_RESPONSE_MODEL:
        messages = self.memory.get()

        if len(self.memory.get()) == 0:
            messages.append(SystemConversationEntry(role="system", content=self.system_prompt))

        messages.append(UserConversationEntry(role="user", content=instructions))

        mcp_tools = [tool.to_mcp_tool() for tool in self.tools] + self._completion_tools(success_response_model, error_response_model)

        self._logger.info(f"Running with messages: {messages} and available tools: {[tool.name for tool in self.tools]}")

        for i in range(1, STEP_LIMIT):
            self._logger.info(f"Running step {i} / {STEP_LIMIT}")
            completion = await self._run_step_async(ctx, messages, mcp_tools)

            if isinstance(completion, success_response_model):
                self._logger.info(f"Completed with response: {completion}")
                return completion

            if isinstance(completion, error_response_model):
                self._logger.info(f"Failed with error: {completion}")
                raise TaskFailureError(self.name, completion)

        raise NoResponseError(self.name)


class FastMCPAgent(BaseFastMCPAgent):
    pass


class PlanningFastMCPAgent(BaseFastMCPAgent):
    pass
