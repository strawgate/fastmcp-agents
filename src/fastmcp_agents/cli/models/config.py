import asyncio
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

import httpx
import yaml
from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.server.server import FastMCP
from fastmcp.tools import Tool as FastMCPTool
from pydantic import Field

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.cli.models.agents import AgentModel
from fastmcp_agents.cli.models.servers import DEFAULT_INIT_TIMEOUT, MCPServerConfigTypes
from fastmcp_agents.cli.models.tools import ExtraToolTypes, ToolTransform
from fastmcp_agents.util.base_model import StrictBaseModel
from fastmcp_agents.vendored.fastmcp_proxy.transforming_proxy import TransformingFastMCPProxy

if TYPE_CHECKING:
    from types import CoroutineType
    from fastmcp.client.transports import FastMCPTransport

BUNDLED_DIR = Path(__file__).parent.parent.parent / "bundled"


class FastMCPAgentsConfig(StrictBaseModel):
    """A configuration for a FastMCP Agents server."""

    name: str | None = Field(default=None)
    """The name of the configuration."""

    agents: list[AgentModel] = Field(default_factory=list)
    """A list of agent models."""

    mcp: dict[str, "MCPServerConfigTypes | FastMCPAgentsConfig | NestedServerConfigTypes"] = Field(default_factory=dict)
    """A dictionary of MCP servers."""

    tools: list[ExtraToolTypes] = Field(default_factory=list)
    """A list of extra tools."""

    async def activate(
        self,
        fastmcp_server: FastMCP[Any] | None = None,
    ) -> tuple[
        FastMCP[Any],
        Sequence[CuratorAgent],
        Sequence[FastMCPTool],
        Sequence[Any],
        Sequence[FastMCP[Any]],
        Sequence[Client[Any]],
    ]:
        """Activate the configuration."""

        if fastmcp_server is None:
            fastmcp_server = FastMCP(name=self.name)

        activated_tools: list[FastMCPTool] = [await tool.activate(fastmcp_server=fastmcp_server) for tool in self.tools]

        nested_servers_and_clients: list[tuple[FastMCP[Any], Client[Any]]] = [
            await server.activate(fastmcp_server=fastmcp_server) for server in self.fastmcp_agent_servers
        ]
        nested_servers = [server for server, _ in nested_servers_and_clients]
        nested_clients = [client for _, client in nested_servers_and_clients]

        mcp_server_tasks: list[CoroutineType[Any, Any, tuple[FastMCP[Any], Client[Any]]]] = [
            mcp.activate(fastmcp_server=fastmcp_server) for mcp in self.mcp_servers
        ]
        activated_mcp_servers: list[tuple[FastMCP[Any], Client[Any]]] = await asyncio.gather(*mcp_server_tasks)
        mcp_servers = [server for server, _ in activated_mcp_servers]
        mcp_clients = [client for _, client in activated_mcp_servers]

        activated_agents: list[CuratorAgent] = [await agent.activate(fastmcp_server=fastmcp_server) for agent in self.agents]

        return (
            fastmcp_server,
            activated_agents,
            activated_tools,
            nested_servers,
            [*mcp_servers, *nested_servers],
            [*mcp_clients, *nested_clients],
        )

    @property
    def mcp_servers(self) -> Sequence[MCPServerConfigTypes]:
        """Get the MCP servers."""
        return [server for server in self.mcp.values() if isinstance(server, MCPServerConfigTypes)]

    @property
    def fastmcp_agent_servers(self) -> Sequence["NestedServerConfigTypes"]:
        """Get the FastMCP agent servers."""
        return [server for server in self.mcp.values() if isinstance(server, (NestedServerConfigTypes))]

    # @field_validator("mcp", mode="after")
    # @classmethod
    # def propagate_mcp_names(cls, v: dict[str, MCPServerConfigTypes]) -> dict[str, MCPServerConfigTypes]:
    #     """Propagate the MCP server names into the server models."""

    #     for name, server in v.items():
    #         if server.name is None:
    #             server.name = name

    #     return v

    @classmethod
    def from_url(cls, url: str) -> "FastMCPAgentsConfig":
        """Load a YAML configuration from a URL."""
        req = httpx.get(url, timeout=10)
        _ = req.raise_for_status()
        return cls._model_validate_yaml(req.text)

    @classmethod
    def from_file(cls, path: str) -> "FastMCPAgentsConfig":
        """Load a YAML configuration from a file."""
        return cls._model_validate_yaml(Path(path).read_text(encoding="utf-8"))

    @classmethod
    def from_bundled(cls, bundle: str) -> "FastMCPAgentsConfig":
        """Load a YAML configuration from a bundled config."""
        this_bundle_dir = BUNDLED_DIR / bundle
        this_bundle_yaml = this_bundle_dir / "server.yml"
        return cls._model_validate_yaml(this_bundle_yaml.read_text(encoding="utf-8"))

    @classmethod
    def _model_validate_yaml(cls, yaml_str: str) -> "FastMCPAgentsConfig":
        """Validate a YAML string."""
        return cls.model_validate(yaml.safe_load(yaml_str))


class NestedServerConfig(StrictBaseModel, ABC):
    """A server that is configured."""

    name: str | None = Field(default=None)
    """The name of the server."""

    tools: dict[str, ToolTransform] = Field(default_factory=dict)
    """The tools to transform."""

    agents_only: bool = Field(default=False)
    """Whether to only activate the agents."""

    tools_only: bool = Field(default=False)
    """Whether to only activate the tools."""

    @abstractmethod
    async def load(self) -> FastMCPAgentsConfig: ...

    async def activate(self, fastmcp_server: FastMCP[Any]) -> tuple[FastMCP[Any], Client[Any]]:
        """Activate the server. Activating a nested server will mount the nested server on the FastMCP server and return a FastMCP server that is a proxy to the nested server."""

        server_config: FastMCPAgentsConfig = await self.load()

        nested_fastmcp_server: FastMCP[Any] = FastMCP(name=self.name,
        include_tags={"agent"} if self.agents_only else None,
        exclude_tags={"agent"} if self.tools_only else None,
        )

        nested_server, _, _, _, _, _ = await server_config.activate(
            fastmcp_server=nested_fastmcp_server,
        )

        client: Client[FastMCPTransport] = Client(transport=nested_server, init_timeout=DEFAULT_INIT_TIMEOUT)

        transforming_proxy_server: TransformingFastMCPProxy = TransformingFastMCPProxy(
            client=client,
            tool_transforms=self.tools,
            include_tags={"agent"} if self.agents_only else None,
            exclude_tags={"agent"} if self.tools_only else None,
        )

        fastmcp_server.mount(server=transforming_proxy_server, as_proxy=True)

        return transforming_proxy_server, client


class FromURLNestedServerConfig(NestedServerConfig):
    """A server that is configured."""

    url: str = Field(...)
    """The URL to fetch the configuration from."""

    @override
    async def load(self) -> FastMCPAgentsConfig:
        """Load the server."""
        return FastMCPAgentsConfig.from_url(self.url)


class FromBundledNestedServerConfig(NestedServerConfig):
    """A server that is configured."""

    bundle: str = Field(...)
    """The bundled server to use for the server."""

    @override
    async def load(self) -> FastMCPAgentsConfig:
        """Load the server."""
        return FastMCPAgentsConfig.from_bundled(self.bundle)


class FromFileNestedServerConfig(NestedServerConfig):
    """A server that is configured."""

    file: str = Field(...)
    """The file to use for the server."""

    @override
    async def load(self) -> FastMCPAgentsConfig:
        """Load the server."""
        return FastMCPAgentsConfig.from_file(self.file)


NestedServerConfigTypes = FromURLNestedServerConfig | FromBundledNestedServerConfig | FromFileNestedServerConfig
