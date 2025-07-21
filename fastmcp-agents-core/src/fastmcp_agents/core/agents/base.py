import json
import logging
from abc import ABC
from collections.abc import Sequence
from logging import Logger
from typing import Any, ClassVar, TypeVar, override

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.mcp_config import MCPConfig, MCPServerTypes
from fastmcp.tools import Tool
from fastmcp.tools.tool import FunctionTool
from fastmcp.tools.tool import Tool as FastMCPTool
from fastmcp.utilities.components import FastMCPComponent
from fastmcp.utilities.mcp_config import mount_mcp_config_into_server  # pyright: ignore[reportUnknownVariableType]
from mcp.types import CallToolResult
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, TypeAdapter

from fastmcp_agents.core.agents.context import AgentRunContext
from fastmcp_agents.core.completions.auto import required_llm
from fastmcp_agents.core.completions.base import BasePendingToolCall, CompletionMessageType, LLMCompletionsProtocol
from fastmcp_agents.core.errors.agents import StepLimitReachedError
from fastmcp_agents.core.utilities.helpers import get_mcp_config

logger: Logger = logging.getLogger(name="fastmcp_agents.agents")

DEFAULT_STEP_LIMIT: int = 10


def get_context() -> Context | None:
    from fastmcp.server.context import _current_context

    return _current_context.get()


def get_fastmcp_from_ctx(ctx: Context) -> FastMCP[Any]:
    """Get the fastmcp from the context."""
    fastmcp: FastMCP[Any] = ctx.fastmcp  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    return fastmcp


class DefaultSuccessModel(BaseModel):
    response: str = Field(
        default=...,
        description="A text response which reflects completion of the task to the requester.",
    )

    steps: list[str] | None = Field(
        default=...,
        description="A list of steps which were taken to complete the task.",
    )


class DefaultFailureModel(BaseModel):
    failure_message: str = Field(
        default=...,
        description="A text response which reflects the failure of task completion to the requester.",
    )

    issues: list[str] | None = Field(
        default=...,
        description="A list of issues which were encountered during task completion.",
    )


SM = TypeVar(name="SM", bound=BaseModel, default=DefaultSuccessModel)
FM = TypeVar(name="FM", bound=BaseModel, default=DefaultFailureModel)


class BaseAgent(FastMCPComponent):
    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True, use_attribute_docstrings=True)

    system_prompt: str = Field(
        default=...,
        description="The system prompt to use for the agent.",
    )

    completions: LLMCompletionsProtocol = Field(
        default_factory=required_llm,
        description="The completions to use for the agent.",
    )

    logger: Logger = Field(default_factory=lambda: logger.getChild(suffix="base_agent"))

    def to_tool(self) -> FunctionTool:
        if not callable(self):
            msg = f"Agent {self.name} does not have a __call__ method."
            raise TypeError(msg)

        return FunctionTool.from_function(
            fn=self.__call__,  # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]
            name=self.name,
            description=self.description,
            tags=self.tags | {"agent"},
            enabled=self.enabled,
        )


def do_nothing(**kwargs: Any) -> None:  # pyright: ignore[reportAny, reportUnusedParameter]
    """Do nothing."""


BASE_TOOLS_AGENT_SYSTEM_PROMPT = """
You are a helpful Tools Agent named `{name}` that has access to tools.

You are described as:
```markdown
{description}
```

You can run many tool calls in a single step but you have a limited number of steps available to complete your task.

If you are asked to do something that would require a tool, but you have no tools available, you will report failure.
"""


class BaseMultiStepAgent(BaseAgent, ABC):
    """A multi-step agent that can be used to run agents."""

    step_limit: int = Field(default=DEFAULT_STEP_LIMIT)

    system_prompt: str = Field(
        default=BASE_TOOLS_AGENT_SYSTEM_PROMPT,
        description="The system prompt to use for the agent.",
    )

    tools: list[Tool] = Field(
        default_factory=list,
        description="Tools that the Agent is always allowed to use.",
    )

    mcp: MCPConfig | dict[str, MCPServerTypes] | dict[str, Any] | None = Field(
        default=None,
        description="""An MCP Config to attach to this Agent. Useful for standalone Agents that do not have a server.
        These tools will always be available to the Agent.""",
    )

    _mcp_proxy: FastMCP[Any] | None = PrivateAttr(default=None)

    _last_run_context: AgentRunContext | None = PrivateAttr(default=None)

    tools_from_context: bool = Field(
        default=False,
        description="Whether to allow the Agent to also use tools from the server.",
    )

    # def add_mcp(self, mcp: MCPConfig | dict[str, MCPServerTypes] | dict[str, Any]) -> None:
    #     mcp_config = get_mcp_config(mcp)

    # @model_validator(mode="after")
    # def validate_tools(self) -> Self:
    #     """Validate the tools."""

    #     if self.tools_from_server and (self.mcp or self.tools):
    #         msg = "mcp and tools cannot be used when tools_from_server is True."
    #         raise ValueError(msg)

    #     return self

    async def _get_tools_from_context(self) -> dict[str, Tool]:
        """Get the tools from the context."""

        if not (ctx := get_context()):
            msg = "No context found to pull tools from."
            raise RuntimeError(msg)

        return await get_fastmcp_from_ctx(ctx=ctx).get_tools()

    async def _get_tools_from_mcp(self) -> dict[str, Tool]:
        """Get the tools from the MCP. Starts the underlying MCP server if it is not already running."""

        if self.mcp is None:
            return {}

        if self._mcp_proxy is not None:
            return await self._mcp_proxy.get_tools()

        mcp_config: MCPConfig = get_mcp_config(mcp=self.mcp)

        mcp_proxy: FastMCP[Any] = FastMCP(name=f"{self.name}-mcp-proxy")

        mount_mcp_config_into_server(config=mcp_config, server=mcp_proxy, name_as_prefix=False)

        self._mcp_proxy = mcp_proxy

        return await mcp_proxy.get_tools()

    async def get_tools(self) -> dict[str, Tool]:
        """Get the tools from the context."""

        base_tools: dict[str, Tool] = {tool.name: tool for tool in self.tools}

        if self.tools_from_context:
            base_tools.update(await self._get_tools_from_context())

        if self.mcp:
            base_tools.update(await self._get_tools_from_mcp())

        return base_tools

    @override
    def model_post_init(self, __context: Any) -> None:  # pyright: ignore[reportAny]
        """Post init."""

        self.logger: Logger = logger.getChild(suffix=self.name)

    @property
    def rendered_system_prompt(self) -> str:
        """The rendered system prompt for the agent."""
        return self.system_prompt.format(
            description=self.description,
            name=self.name,
            tags=self.tags,
        )

    async def _report_progress_and_log(
        self,
        *,
        message: str,
        progress: float | None = None,
        internal_message: str | None = None,
    ) -> None:
        """Report information to the user."""

        if ctx := get_context():
            if progress:
                await ctx.report_progress(message=message, progress=progress)
            else:
                await ctx.info(message=message, logger_name=self.logger.name)

        if internal_message:
            self.logger.info(msg=f"{message} -- {internal_message}")
        else:
            self.logger.info(msg=message)

    def _success_tool[SM: BaseModel](self, success_model: type[SM]) -> Tool:
        """The tool to report success of the task."""

        return FunctionTool(
            fn=do_nothing,
            name="success",
            description="Report success of the task.",
            parameters=TypeAdapter[SM](success_model).json_schema(),
        )

    def _failure_tool[FM: BaseModel](self, failure_model: type[FM]) -> Tool:
        return FunctionTool(
            fn=do_nothing,
            name="failure",
            description="Report failure of the task.",
            parameters=TypeAdapter[FM](failure_model).json_schema(),
        )

    async def pick_tools(
        self,
        *,
        messages: Sequence[CompletionMessageType | str],
        tools: Sequence[FastMCPTool],
    ) -> tuple[CompletionMessageType | str, Sequence[BasePendingToolCall]]:
        """Pick the tools to use for the agent."""

        extras, message, recommended_tool_calls = await self.completions.tools(
            system_prompt=self.rendered_system_prompt,
            messages=list(messages),
            tools=tools,
        )

        self.logger.debug(msg=f"Agent has picked tools: {[tool.tool.name for tool in recommended_tool_calls]}")

        if extras.thinking:
            self.logger.info(msg=f"Agent gave it some thought: {extras.thinking}")

        return message, recommended_tool_calls

    async def check_for_completion(
        self, pending_tool_calls: Sequence[BasePendingToolCall], success_model: type[SM], failure_model: type[FM]
    ) -> SM | FM | None:
        """Check for completion of the task."""

        for pending_tool_call in pending_tool_calls:
            if pending_tool_call.tool.name in {"success", "failure"}:
                return TypeAdapter[SM | FM](success_model | failure_model).validate_python(pending_tool_call.arguments)

        return None

    async def invoke_tools(
        self,
        *,
        run_context: AgentRunContext | None = None,
        pending_tool_calls: Sequence[BasePendingToolCall],
    ) -> Sequence[CompletionMessageType]:
        """Invoke the tools."""

        await self._report_progress_and_log(
            message=f"Agent is calling {len(pending_tool_calls)} tools",
            internal_message=f"{[tool.tool.name for tool in pending_tool_calls]}",
        )

        tool_result_messages: Sequence[CompletionMessageType] = []

        for pending_tool_call in pending_tool_calls:
            if len(pending_tool_calls) > 1:
                self.logger.info(msg=f"Calling tool: {pending_tool_call.tool.name}")

            self.logger.debug(msg=f"Tool {pending_tool_call.tool.name} has arguments: {json.dumps(pending_tool_call.arguments)[:500]}...")

            message, tool_call_result = await pending_tool_call.run()

            tool_result_messages.append(message)

            if isinstance(tool_call_result, ToolError):
                self.logger.error(msg=f"Tool {pending_tool_call.tool.name} has returned an error: {tool_call_result}")

                if run_context:
                    run_context.failed_tool_calls.append(pending_tool_call.tool.name)

                continue

            self.logger.debug(msg=f"Tool {pending_tool_call.tool.name} has returned: {trim_tool_call_result(tool_call_result)}...")

            if run_context:
                run_context.successful_tool_calls.append(pending_tool_call.tool.name)

        return tool_result_messages

    async def run_step[SM: BaseModel, FM: BaseModel](
        self,
        *,
        messages: Sequence[CompletionMessageType | str],
        tools: Sequence[FastMCPTool],
        step_number: int,
        step_limit: int,
        success_model: type[SM],
        failure_model: type[FM],
        run_context: AgentRunContext | None = None,
    ) -> tuple[Sequence[CompletionMessageType | str], SM | FM | None]:
        """Run a single step of the agent."""

        await self._report_progress_and_log(
            message=f"Agent is running step {step_number} of {step_limit}...",
            progress=step_number / step_limit,
        )

        assistant_message, recommended_tool_calls = await self.pick_tools(
            messages=messages,
            tools=[*tools, self._success_tool(success_model=success_model), self._failure_tool(failure_model=failure_model)],
        )

        tool_result_messages = await self.invoke_tools(
            run_context=run_context,
            pending_tool_calls=recommended_tool_calls,
        )

        if completed := await self.check_for_completion(
            pending_tool_calls=recommended_tool_calls,
            success_model=success_model,
            failure_model=failure_model,
        ):
            self.logger.info(msg=f"Agent has reported completion: {completed.model_dump_json(indent=2)}")

            return [assistant_message, *tool_result_messages], completed

        return [assistant_message, *tool_result_messages], None

    async def run_steps[SM: BaseModel, FM: BaseModel](
        self,
        *,
        tools: Sequence[FastMCPTool] | dict[str, FastMCPTool],
        messages: Sequence[CompletionMessageType],
        success_model: type[SM] = DefaultSuccessModel,
        failure_model: type[FM] = DefaultFailureModel,
    ) -> tuple[Sequence[CompletionMessageType | str], SM | FM]:
        """Run the multi-step agent.

        The agent will run until it is completed or the step limit is reached.

        Args:
            tools: The tools to use for the agent.
            messages: The initial messages to use for the agent.

        Returns:
            tuple[Sequence[CompletionMessageType], success_model | failure_model]: The conversation messages and the completion result.
        """

        if isinstance(tools, dict):
            tools = list(tools.values())

        await self._report_progress_and_log(
            message=f"Agent {self.name} is running steps...",
            internal_message=f"with step limit {self.step_limit} and tools: {[tool.name for tool in tools]}",
        )

        running_messages: list[CompletionMessageType | str] = list(messages)

        run_context: AgentRunContext = AgentRunContext(messages=running_messages)
        self._last_run_context = run_context

        for i in range(self.step_limit):
            new_messages, success_or_failure = await self.run_step(
                run_context=run_context,
                messages=running_messages,
                tools=tools,
                step_number=i,
                step_limit=self.step_limit,
                success_model=success_model,
                failure_model=failure_model,
            )

            running_messages.extend(new_messages)

            if success_or_failure:
                run_context.mark_end_time()

                await self._report_progress_and_log(
                    message=f"Agent {self.name} has finished running steps in {run_context.duration}.",
                    progress=1.0,
                )
                self.logger.info(
                    msg=f"Agent {self.name} used {run_context.tool_count} tools while running: {run_context.tool_call_summary}"
                )

                return running_messages, success_or_failure

        run_context.mark_end_time()

        self.logger.error(msg=f"Step limit reached for agent {self.name} with step limit {self.step_limit}.")

        raise StepLimitReachedError(agent_name=self.name, step_limit=self.step_limit)


def trim_tool_call_result(tool_call_result: CallToolResult, length: int = 500) -> str:
    """Trim the tool call result.
    
    Args:
        tool_call_result: The tool call result to trim.
        length: The length to trim the tool call result to.
    """

    output: str

    if tool_call_result.structured_content:
        output = json.dumps(tool_call_result.structured_content, indent=2)
    else:
        output = "\n".join([content.text for content in tool_call_result.content])

    return output[:length]