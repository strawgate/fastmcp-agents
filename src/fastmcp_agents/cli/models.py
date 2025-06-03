from typing import TYPE_CHECKING, Any, Literal

from fastmcp import Client, FastMCP
from fastmcp.server.proxy import ProxyTool
from fastmcp.tools import Tool as FastMCPTool
from fastmcp.utilities.mcp_config import MCPConfig, RemoteMCPServer, StdioMCPServer
from pydantic import BaseModel, Field

from fastmcp_agents.agent.basic import FastMCPAgent
from fastmcp_agents.agent.planning import PlanningFastMCPAgent
from fastmcp_agents.conversation.memory.ephemeral import EphemeralMemory
from fastmcp_agents.errors.cli import MCPServerError
from fastmcp_agents.observability.logging import BASE_LOGGER
from fastmcp_agents.vendored.tool_transformer.models import ToolOverride

if TYPE_CHECKING:
    from collections.abc import Callable

logger = BASE_LOGGER.getChild("agent.loader")


class ServerSettings(BaseModel):
    transport: Literal["stdio", "sse", "streamable-http"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    agent_only: bool = False
    tool_only: bool = False


class BaseExtraTool(BaseModel):
    """A set of overrides for a tool."""

    name: str
    description: str

    def to_fastmcp_tool(self) -> FastMCPTool:
        msg = "Subclasses must implement this method."
        raise NotImplementedError(msg)


class StaticExtraTool(BaseExtraTool):
    returns: str

    def to_fastmcp_tool(self) -> FastMCPTool:
        def tool_fn() -> str:
            return self.returns

        return FastMCPTool.from_function(
            fn=tool_fn,
            name=self.name,
            description=self.description,
        )


ExtraToolTypes = StaticExtraTool


async def _wrap_client_tools(client: Client, tool_overrides: dict[str, ToolOverride]) -> list[FastMCPTool]:
    async with client:
        client_tools = await client.list_tools()

    proxied_client_tools = [await ProxyTool.from_client(client, client_tool) for client_tool in client_tools]

    return [
        tool_overrides[proxied_client_tool.name].apply_to_tool(proxied_client_tool)
        if proxied_client_tool.name in tool_overrides
        else proxied_client_tool
        for proxied_client_tool in proxied_client_tools
    ]


class OverriddenStdioMCPServer(StdioMCPServer):
    """A Stdio server with overridden tools."""

    tools: dict[str, ToolOverride] = Field(default_factory=dict[str, ToolOverride])

    def to_fastmcp_client(self, init_timeout: float = 10.0) -> Client:
        transport = self.to_transport()
        transport.keep_alive = True
        return Client(transport=transport, init_timeout=init_timeout)

    async def to_wrapped_client(self) -> tuple[Client, list[FastMCPTool]]:
        client = self.to_fastmcp_client()
        return client, await _wrap_client_tools(client, self.tools)


class OverriddenRemoteMCPServer(RemoteMCPServer):
    """A Remote server with overridden tools."""

    tools: dict[str, ToolOverride] = Field(default_factory=dict)

    def to_fastmcp_client(self, init_timeout: float = 10.0) -> Client:
        return Client(transport=self.to_transport(), init_timeout=init_timeout)

    async def to_wrapped_client(self) -> tuple[Client, list[FastMCPTool]]:
        client = self.to_fastmcp_client()
        return client, await _wrap_client_tools(client, self.tools)


class OverriddenMCPConfig(MCPConfig):
    mcpServers: dict[str, OverriddenStdioMCPServer | OverriddenRemoteMCPServer] = Field(default_factory=dict)  # type: ignore # noqa: N815


class AgentModel(BaseModel):
    type: Literal["fastmcp"] = "fastmcp"
    name: str = Field(..., description="The name of the agent.")
    description: str = Field(..., description="The description of the agent.")
    default_instructions: str = Field(..., description="The default instructions to provide to the agent.")
    model: str | None = Field(default=None, description="The GenAI model to use for the agent.")
    allowed_tools: list[str] | None = Field(None, description="An optional list of the tools to provide to the agent.")
    blocked_tools: list[str] | None = Field(None, description="An optional list of the tools to block from the agent.")

    @classmethod
    def to_fastmcp_agent(cls, agent_model: "AgentModel", tools: list[FastMCPTool]) -> FastMCPAgent:
        agent_tools = list(tools)

        if agent_model.allowed_tools:
            agent_tools = [tool for tool in agent_tools if tool.name in agent_model.allowed_tools]

        if agent_model.blocked_tools:
            agent_tools = [tool for tool in agent_tools if tool.name not in agent_model.blocked_tools]

        logger.debug(f"Agent {agent_model.name} will have access to the following tools: {agent_tools}")

        return FastMCPAgent(
            name=agent_model.name,
            description=agent_model.description,
            system_prompt=agent_model.default_instructions,
            default_tools=agent_tools,
            memory_factory=EphemeralMemory,
        )

    @classmethod
    def to_fastmcp_tool(cls, agent_model: "AgentModel", tools: list[FastMCPTool]) -> tuple[FastMCPAgent, FastMCPTool]:
        agent = cls.to_fastmcp_agent(agent_model, tools)

        return agent, FastMCPTool.from_function(fn=agent.currate, name=agent.name, description=agent.description)


class AugmentedServerModel(BaseModel):
    """A full configuration for an augmented server with Agents and extra tools."""

    agents: list[AgentModel] = Field(default_factory=list)
    mcpServers: dict[str, OverriddenStdioMCPServer | OverriddenRemoteMCPServer] = Field(default_factory=dict)  # noqa: N815
    tools: list[ExtraToolTypes] = Field(default_factory=list)

    async def to_fastmcp_server(self, server_settings: ServerSettings) -> tuple[list[FastMCPAgent], list[Client], FastMCP]:
        wrapped_mcp_clients: list[tuple[Client, list[FastMCPTool]]] = []

        for name, server in self.mcpServers.items():
            try:
                wrapped_mcp_clients.append(await server.to_wrapped_client())
            except Exception as e:  # noqa: PERF203
                raise MCPServerError(name, e) from e

        mcp_tools = [tool for _, tools in wrapped_mcp_clients for tool in tools]
        extra_tools = [extra_tool.to_fastmcp_tool() for extra_tool in self.tools]
        all_standard_tools: list[FastMCPTool] = mcp_tools + extra_tools

        exposed_tools: list[FastMCPTool | Callable[..., Any]] = []
        fastmcp_agents: list[FastMCPAgent] = []

        if not server_settings.tool_only:
            for agent_model in self.agents:
                fastmcp_agent, agent_tool = AgentModel.to_fastmcp_tool(agent_model, all_standard_tools)

                fastmcp_agents.append(fastmcp_agent)
                exposed_tools.append(agent_tool)

        if not server_settings.agent_only:
            exposed_tools.extend(all_standard_tools)

        return fastmcp_agents, [client for client, _ in wrapped_mcp_clients], FastMCP(name="augmented-server", tools=exposed_tools)
