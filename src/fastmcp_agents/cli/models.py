"""Pydantic models for the CLI."""

import os
import sys
from collections.abc import Sequence
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Literal

from fastmcp import Client, FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server.proxy import ProxyTool
from fastmcp.tools import FunctionTool
from fastmcp.tools import Tool as FastMCPTool
from fastmcp.utilities.mcp_config import MCPConfig, RemoteMCPServer, StdioMCPServer
from pydantic import BaseModel, Field

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.agent.multi_step import MultiStepAgent
from fastmcp_agents.errors.cli import MCPServerStartupError
from fastmcp_agents.llm_link.litellm import LitellmLLMLink
from fastmcp_agents.observability.logging import BASE_LOGGER
from fastmcp_agents.vendored.tool_transformer.models import ToolOverride

if TYPE_CHECKING:
    from collections.abc import Callable

logger = BASE_LOGGER.getChild("agent.loader")


class ServerSettings(BaseModel):
    """Settings for the server."""

    transport: Literal["stdio", "sse", "streamable-http"] = Field(..., description="The transport to use for the server.")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(..., description="The log level to use for the server.")
    agent_only: bool = Field(default=False, description="Whether to only run the agents.")
    tool_only: bool = Field(default=False, description="Whether to only run the tools.")
    mutable_agents: bool = Field(default=False, description="Whether to publish a tool to mutate the Agent's System Prompt.")


class BaseExtraTool(BaseModel):
    """A set of overrides for a tool."""

    name: str = Field(..., description="The name of the tool.")
    description: str = Field(..., description="The description of the tool.")

    def to_fastmcp_tool(self) -> FastMCPTool:
        msg = "Subclasses must implement this method."
        raise NotImplementedError(msg)


class StaticExtraTool(BaseExtraTool):
    """A tool that returns a static string."""

    returns: str = Field(..., description="The string to return from the tool.")

    def to_fastmcp_tool(self) -> FunctionTool:
        """Convert the tool to a FastMCP tool."""

        def tool_fn() -> str:
            return self.returns

        return FunctionTool.from_function(
            fn=tool_fn,
            name=self.name,
            description=self.description,
        )


ExtraToolTypes = StaticExtraTool


async def _wrap_client_tools(client: Client, tool_overrides: dict[str, ToolOverride], name: str) -> Sequence[FastMCPTool]:
    """Wrap the client's tools with the tool overrides."""

    logger.info(f"Starting MCP server {name}")

    async with client:
        try:
            await client.ping()
        except RuntimeError as re:
            logger.exception(msg=f"An error occurred while pinging the underlying server {name}. Unable to start the underlying server.")
            raise MCPServerStartupError(name) from re

        client_tools = await client.list_tools()

    proxied_client_tools = [await ProxyTool.from_client(client, client_tool) for client_tool in client_tools]

    return [
        tool_overrides[proxied_client_tool.name].apply_to_tool(proxied_client_tool)
        if proxied_client_tool.name in tool_overrides
        else proxied_client_tool
        for proxied_client_tool in proxied_client_tools
    ]


class FastMCPAgentServer(BaseModel):
    config: str | list[str] = Field(..., description="The config to use for the server.")
    tools: dict[str, ToolOverride] = Field(default_factory=dict)


class FastMCPAgentsStdioTransport(StdioTransport):
    """Transport for running Python modules."""

    def __init__(
        self,
        args: list[str],
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        keep_alive: bool | None = None,
    ):
        """
        Initialize a Python transport.

        Args:
            script_path: Path to the Python script to run
            args: Additional arguments to pass to the script
            env: Environment variables to set for the subprocess
            cwd: Current working directory for the subprocess
            python_cmd: Python command to use (default: "python")
            keep_alive: Whether to keep the subprocess alive between connections.
                       Defaults to True. When True, the subprocess remains active
                       after the connection context exits, allowing reuse in
                       subsequent connections.
        """

        if len(args) == 0:
            msg = "No arguments provided to the FastMCPAgentsStdioTransport."
            raise ValueError(msg)

        # python
        command = sys.executable

        # python -m fastmcp_agents.cli.base
        base_args = ["-m", "fastmcp_agents.cli.base"]

        full_args = base_args + args

        super().__init__(
            command=command,
            args=full_args,
            env=env,
            cwd=cwd,
            keep_alive=keep_alive,
        )


def strip_uv_uvx_python_args(command: str, args: list[str]) -> list[str]:
    """Strip the first couple of args if they are uv run or uvx."""

    new_args = deepcopy(args)

    if command == "uv" and args[0] == "run" and args[1] == "fastmcp_agents":
        new_args = args[2:]

    if command == "uvx" and args[0] == "fastmcp_agents":
        new_args = args[1:]

    return new_args


class OverriddenStdioMCPServer(StdioMCPServer):
    """A Stdio server with overridden tools."""

    tools: dict[str, ToolOverride] = Field(default_factory=dict[str, ToolOverride])

    def to_fastmcp_client(self, init_timeout: float = 20.0) -> Client:
        """Convert the server to a FastMCP client."""

        new_envs = os.environ.copy()
        new_envs.update(self.env)
        self.env = new_envs
        transport = self.to_transport()

        if self.command in {"uv", "uvx", "python"} and "fastmcp_agents" in self.args:
            transport = FastMCPAgentsStdioTransport(args=strip_uv_uvx_python_args(self.command, self.args), env=new_envs, cwd=self.cwd)
        transport.keep_alive = True
        return Client(transport=transport, init_timeout=init_timeout)

    async def to_wrapped_client(self, name: str) -> tuple[Client, Sequence[FastMCPTool]]:
        """Convert the server to a wrapped FastMCP client."""
        client = self.to_fastmcp_client()
        return client, await _wrap_client_tools(client, self.tools, name)


class OverriddenRemoteMCPServer(RemoteMCPServer):
    """A Remote server with overridden tools."""

    tools: dict[str, ToolOverride] = Field(default_factory=dict)

    def to_fastmcp_client(self, init_timeout: float = 10.0) -> Client:
        """Convert the server to a FastMCP client."""
        return Client(transport=self.to_transport(), init_timeout=init_timeout)

    async def to_wrapped_client(self, name: str) -> tuple[Client, Sequence[FastMCPTool]]:
        """Convert the server to a wrapped FastMCP client."""
        client = self.to_fastmcp_client()
        return client, await _wrap_client_tools(client, self.tools, name)


class OverriddenMCPConfig(MCPConfig):
    """A MCP config with overridden tools."""

    mcpServers: dict[str, OverriddenStdioMCPServer | OverriddenRemoteMCPServer] = Field(default_factory=dict)  # type: ignore # noqa: N815


class AgentModel(BaseModel):
    """A model for an agent."""

    type: Literal["fastmcp"] = Field(default="fastmcp", description="The type of agent.")
    name: str = Field(..., description="The name of the agent.")
    description: list[str] | str = Field(..., description="The description of the agent.")
    instructions: list[str] | str = Field(..., description="The default instructions to provide to the agent.")
    model: str | None = Field(default=None, description="The GenAI model to use for the agent.")
    allowed_tools: list[str] | None = Field(None, description="An optional list of the tools to provide to the agent.")
    blocked_tools: list[str] | None = Field(None, description="An optional list of the tools to block from the agent.")

    @classmethod
    def to_curator_agent(cls, agent_model: "AgentModel", tools: Sequence[FastMCPTool]) -> CuratorAgent:
        """Convert the agent model to a FastMCP agent."""
        agent_tools = list(tools)

        if agent_model.allowed_tools:
            agent_tools = [tool for tool in agent_tools if tool.name in agent_model.allowed_tools]

        if agent_model.blocked_tools:
            agent_tools = [tool for tool in agent_tools if tool.name not in agent_model.blocked_tools]

        logger.debug(f"Agent {agent_model.name} will have access to the following tools: {agent_tools}")

        agent_description = agent_model.description if isinstance(agent_model.description, str) else "\n".join(agent_model.description)
        agent_instructions = agent_model.instructions if isinstance(agent_model.instructions, str) else "\n".join(agent_model.instructions)

        return CuratorAgent(
            name=agent_model.name,
            description=agent_description,
            instructions=agent_instructions,
            default_tools=agent_tools,
            llm_link=LitellmLLMLink(),
        )

    @classmethod
    def to_fastmcp_tool(cls, agent_model: "AgentModel", tools: Sequence[FastMCPTool]) -> tuple[CuratorAgent, FastMCPTool]:
        """Convert the agent model to a FastMCP tool."""
        agent = cls.to_curator_agent(agent_model, tools)

        return agent, FunctionTool.from_function(fn=agent.perform_task, name=agent.name, description=agent.description)


class AugmentedServerModel(BaseModel):
    """A full configuration for an augmented server with Agents and extra tools."""

    agents: list[AgentModel] = Field(default_factory=list)
    mcpServers: dict[str, OverriddenStdioMCPServer | OverriddenRemoteMCPServer] = Field(default_factory=dict)  # noqa: N815
    tools: list[ExtraToolTypes] = Field(default_factory=list)

    async def to_fastmcp_server(self, server_settings: ServerSettings) -> tuple[Sequence[MultiStepAgent], list[Client], FastMCP]:
        """Convert the server model to a FastMCP server, agents, and tools."""

        wrapped_mcp_clients: list[tuple[Client, Sequence[FastMCPTool]]] = []

        for name, server in self.mcpServers.items():
            wrapped_mcp_clients.append(await server.to_wrapped_client(name=name))

        mcp_tools = [tool for _, tools in wrapped_mcp_clients for tool in tools]
        extra_tools = [extra_tool.to_fastmcp_tool() for extra_tool in self.tools]
        all_standard_tools: Sequence[FastMCPTool] = mcp_tools + extra_tools

        exposed_tools: Sequence[FastMCPTool | Callable[..., Any]] = []
        fastmcp_agents: list[CuratorAgent] = []

        if not server_settings.tool_only:
            for agent_model in self.agents:
                fastmcp_agent, agent_tool = AgentModel.to_fastmcp_tool(agent_model, all_standard_tools)

                if server_settings.mutable_agents:
                    exposed_tools.append(
                        FunctionTool.from_function(fn=fastmcp_agent.get_instructions, name=agent_model.name + "_get_instructions")
                    )
                    exposed_tools.append(
                        FunctionTool.from_function(fn=fastmcp_agent.change_instructions, name=agent_model.name + "_change_instructions")
                    )
                    exposed_tools.append(
                        FunctionTool.from_function(
                            fn=fastmcp_agent.perform_task_return_conversation, name=agent_model.name + "_trace_conversation"
                        )
                    )

                fastmcp_agents.append(fastmcp_agent)
                exposed_tools.append(agent_tool)

        if not server_settings.agent_only:
            exposed_tools.extend(all_standard_tools)

        return fastmcp_agents, [client for client, _ in wrapped_mcp_clients], FastMCP(name="augmented-server", tools=exposed_tools)
