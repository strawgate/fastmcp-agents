"""Pydantic models for the CLI."""

from typing import Any

from fastmcp import FastMCP
from fastmcp.client.client import Client
from fastmcp.utilities.mcp_config import RemoteMCPServer as FastMCPRemoteMCPServer
from fastmcp.utilities.mcp_config import StdioMCPServer as FastMCPStdioMCPServer
from pydantic import Field

from fastmcp_agents.cli.models.tools import ToolTransform
from fastmcp_agents.vendored.fastmcp_proxy.transforming_proxy import TransformingFastMCPProxy

DEFAULT_INIT_TIMEOUT = 20


class StdioMCPServerConfig(FastMCPStdioMCPServer):
    """A Stdio server with tool transforms."""

    tools: dict[str, ToolTransform] = Field(default_factory=dict)
    """The tools to transform."""

    name: str | None = Field(default=None)
    """The name of the server."""

    async def activate(self, fastmcp_server: FastMCP[Any]) -> tuple[FastMCP[Any], Client[Any]]:
        """Activate the server."""

        transport = self.to_transport()

        transport.keep_alive = True

        client = Client(transport=transport, init_timeout=DEFAULT_INIT_TIMEOUT)

        transforming_proxy_server = TransformingFastMCPProxy(client=client, tool_transforms=self.tools)

        fastmcp_server.mount(server=transforming_proxy_server, as_proxy=True)

        return transforming_proxy_server, client


class RemoteMCPServerConfig(FastMCPRemoteMCPServer):
    """A Remote server with tool transforms."""

    name: str | None = Field(default=None)
    """The name of the server."""

    tools: dict[str, ToolTransform] = Field(default_factory=dict)
    """The tools to transform."""

    async def activate(self, fastmcp_server: FastMCP[Any]) -> tuple[FastMCP[Any], Client[Any]]:
        """Activate the server."""

        transport = self.to_transport()

        client = Client(transport=transport, init_timeout=DEFAULT_INIT_TIMEOUT)

        transforming_proxy_server = TransformingFastMCPProxy(client=client, tool_transforms=self.tools)

        fastmcp_server.mount(server=transforming_proxy_server)

        return transforming_proxy_server, client


# class NestedServerConfig(BaseStrictModel):
#     """A server that is configured."""

#     name: str | None = Field(default=None)
#     """The name of the server."""

#     tools: dict[str, ToolTransform] = Field(default_factory=dict)
#     """The tools to transform."""

#     @abstractmethod
#     async def load(self) -> "FastMCPAgentsConfig": ...

#     async def activate(self, fastmcp_server: FastMCP) -> None:
#         """Activate the server."""

#         server_config = await self.load()

#         activated_server = await server_config.activate()

#         client = Client(transport=activated_server, init_timeout=DEFAULT_INIT_TIMEOUT)

#         transforming_proxy_server = TransformingFastMCPProxy(client=client, tool_transforms=self.tools)

#         fastmcp_server.mount(server=transforming_proxy_server)


# class FromURLNestedServerConfig(NestedServerConfig):
#     """A server that is configured."""

#     url: str = Field(...)
#     """The URL to fetch the configuration from."""

#     @override
#     async def load(self) -> "FastMCPAgentsConfig":
#         """Load the server."""
#         from fastmcp_agents.cli.models.config import FastMCPAgentsConfig

#         return FastMCPAgentsConfig.from_url(self.url)


# class FromBundledNestedServerConfig(NestedServerConfig):
#     """A server that is configured."""

#     bundle: str = Field(...)
#     """The bundled server to use for the server."""

#     @override
#     async def load(self) -> "FastMCPAgentsConfig":
#         """Load the server."""
#         from fastmcp_agents.cli.models.config import FastMCPAgentsConfig

#         return FastMCPAgentsConfig.from_bundled(self.bundle)


# class FromFileNestedServerConfig(NestedServerConfig):
#     """A server that is configured."""

#     file: str = Field(...)
#     """The file to use for the server."""

#     @override
#     async def load(self) -> "FastMCPAgentsConfig":
#         """Load the server."""
#         from fastmcp_agents.cli.models.config import FastMCPAgentsConfig

#         return FastMCPAgentsConfig.from_file(self.file)


MCPServerConfigTypes = StdioMCPServerConfig | RemoteMCPServerConfig


# class FastMCPAgentsStdioTransport(StdioTransport):
#     """Transport for running Python modules."""

#     def __init__(
#         self,
#         args: list[str],
#         env: dict[str, str] | None = None,
#         cwd: str | None = None,
#         keep_alive: bool | None = None,
#     ):
#         """
#         Initialize a Python transport.

#         Args:
#             script_path: Path to the Python script to run
#             args: Additional arguments to pass to the script
#             env: Environment variables to set for the subprocess
#             cwd: Current working directory for the subprocess
#             python_cmd: Python command to use (default: "python")
#             keep_alive: Whether to keep the subprocess alive between connections.
#                        Defaults to True. When True, the subprocess remains active
#                        after the connection context exits, allowing reuse in
#                        subsequent connections.
#         """

#         if len(args) == 0:
#             msg = "No arguments provided to the FastMCPAgentsStdioTransport."
#             raise ValueError(msg)

#         # python
#         command = sys.executable

#         # python -m fastmcp_agents.cli.base
#         base_args = ["-m", "fastmcp_agents.cli.base"]

#         full_args = base_args + args

#         super().__init__(
#             command=command,
#             args=full_args,
#             env=env,
#             cwd=cwd,
#             keep_alive=keep_alive,
#         )


# class FastMCPAgentsServerConfig(BaseStrictModel):
#     """A server that is configured."""

#     name: str | None = Field(default=None)
#     """The name of the server."""

#     url: str | None = Field(default=None)
#     """The URL to fetch the configuration from."""

#     bundle: str | None = Field(default=None)
#     """The bundled server to use for the server."""

#     file: str | None = Field(default=None)
#     """The file to use for the server."""

#     @model_validator(mode="after")
#     def validate_config(self) -> "FastMCPAgentsServerConfig":
#         """Validate the configuration."""
#         if self.url is None and self.bundle is None and self.file is None:
#             msg = "Either url, bundle, or file must be provided."
#             raise ValueError(msg)

#         # only one of the three can be provided
#         if sum(1 for v in [self.url, self.bundle, self.file] if v is not None) != 1:
#             msg = "Only one of url, bundle, or file must be provided."
#             raise ValueError(msg)

#         return self


# class BundledFastMCPAgentsServerConfig(BaseStrictModel):
#     """A bundled server."""

#     bundle: str | None = Field(default=None)
#     """The bundled server to use for the server."""

#     @field_validator("bundle")
#     @classmethod
#     def validate_bundle(cls, v: str | None) -> str | None:
#         """Validate the bundle."""
#         if v is None:
#             return None

#         bundled_server_path = BUNDLED_DIR / v / "server.yml"
#         if not bundled_server_path.exists():
#             msg = f"Bundled server {v} does not exist."
#             raise ValueError(msg)

#         return str(bundled_server_path)


# def strip_uv_uvx_python_args(command: str, args: list[str]) -> list[str]:
#     """Strip the first couple of args if they are uv run or uvx."""

#     new_args = deepcopy(args)

#     if command == "uv" and args[0] == "run" and args[1] == "fastmcp_agents":
#         new_args = args[2:]

#     if command == "uvx" and args[0] == "fastmcp_agents":
#         new_args = args[1:]

#     return new_args


# class OverriddenStdioMCPServer(StdioMCPServer):
#     """A Stdio server with overridden tools."""

#     tools: dict[str, ToolOverride] = Field(default_factory=dict[str, ToolOverride])

#     def to_fastmcp_client(self, init_timeout: float = DEFAULT_INIT_TIMEOUT) -> Client:
#         """Convert the server to a FastMCP client."""

#         new_envs = os.environ.copy()
#         new_envs.update(self.env)
#         self.env = new_envs
#         transport = self.to_transport()

#         if self.command in {"uv", "uvx", "python"} and "fastmcp_agents" in self.args:
#             transport = FastMCPAgentsStdioTransport(args=strip_uv_uvx_python_args(self.command, self.args), env=new_envs, cwd=self.cwd)
#         transport.keep_alive = True
#         return Client(transport=transport, init_timeout=init_timeout)

#     async def to_wrapped_client(self, name: str) -> tuple[Client, Sequence[FastMCPTool]]:
#         """Convert the server to a wrapped FastMCP client."""
#         client = self.to_fastmcp_client()
#         logger.info(f"Running {name} with cli: {self.command} {self.args}")
#         return client, await _wrap_client_tools(client, self.tools, name)


# class OverriddenRemoteMCPServer(RemoteMCPServer):
#     """A Remote server with overridden tools."""

#     tools: dict[str, ToolOverride] = Field(default_factory=dict)

#     def to_fastmcp_client(self, init_timeout: float = DEFAULT_INIT_TIMEOUT) -> Client:
#         """Convert the server to a FastMCP client."""
#         return Client(transport=self.to_transport(), init_timeout=init_timeout)

#     async def to_wrapped_client(self, name: str) -> tuple[Client, Sequence[FastMCPTool]]:
#         """Convert the server to a wrapped FastMCP client."""
#         client = self.to_fastmcp_client()
#         logger.info(f"Running {name} with cli: {self.url}")
#         return client, await _wrap_client_tools(client, self.tools, name)


# class OverriddenMCPConfig(MCPConfig):
#     """A MCP config with overridden tools."""

#     mcpServers: dict[str, OverriddenStdioMCPServer | OverriddenRemoteMCPServer] = Field(default_factory=dict)  # type: ignore


# class AugmentedServerModel(BaseStrictModel):
#     """A full configuration for an augmented server with Agents and extra tools."""

#     agents: list[AgentModel] = Field(default_factory=list)
#     mcpServers: dict[str, OverriddenStdioMCPServer | OverriddenRemoteMCPServer] = Field(default_factory=dict)
#     tools: list[ExtraToolTypes] = Field(default_factory=list)

#     async def to_fastmcp_server(self, server_settings: ServerSettings) -> tuple[Sequence[MultiStepAgent], list[Client], FastMCP]:
#         """Convert the server model to a FastMCP server, agents, and tools."""

#         wrapped_mcp_clients: list[tuple[Client, Sequence[FastMCPTool]]] = []

#         for name, server in self.mcpServers.items():
#             wrapped_mcp_clients.append(await server.to_wrapped_client(name=name))

#         mcp_tools = [tool for _, tools in wrapped_mcp_clients for tool in tools]
#         extra_tools = [extra_tool.to_fastmcp_tool() for extra_tool in self.tools]
#         all_standard_tools: Sequence[FastMCPTool] = mcp_tools + extra_tools

#         exposed_tools: Sequence[FastMCPTool | Callable[..., Any]] = []
#         fastmcp_agents: list[CuratorAgent] = []

#         if not server_settings.tool_only:
#             for agent_model in self.agents:
#                 fastmcp_agent, agent_tool = AgentModel.to_fastmcp_tool(agent_model, all_standard_tools)

#                 if server_settings.mutable_agents:
#                     exposed_tools.append(
#                         FunctionTool.from_function(fn=fastmcp_agent.get_instructions, name=agent_model.name + "_get_instructions")
#                     )
#                     exposed_tools.append(
#                         FunctionTool.from_function(fn=fastmcp_agent.change_instructions, name=agent_model.name + "_change_instructions")
#                     )
#                     exposed_tools.append(
#                         FunctionTool.from_function(
#                             fn=fastmcp_agent.perform_task, name=agent_model.name + "_trace_conversation"
#                         )
#                     )

#                 fastmcp_agents.append(fastmcp_agent)
#                 exposed_tools.append(agent_tool)

#         if not server_settings.agent_only:
#             exposed_tools.extend(all_standard_tools)

#         return (
#             fastmcp_agents,
#             [client for client, _ in wrapped_mcp_clients],
#             FastMCP(
#                 name="augmented-server",
#                 tools=exposed_tools,
#                 mask_error_details=False,
#             ),
#         )
