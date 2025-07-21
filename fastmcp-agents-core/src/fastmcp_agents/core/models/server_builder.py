from collections.abc import Sequence
from pathlib import Path
from typing import Any, Self

import yaml
from fastmcp.client import Client
from fastmcp.mcp_config import MCPConfig, MCPServerTypes
from fastmcp.server import FastMCP
from fastmcp.tools.tool_transform import ToolTransformConfig
from fastmcp.utilities.mcp_config import mount_mcp_config_into_server
from pydantic import BaseModel, ConfigDict, Field

from fastmcp_agents.core.agents.base import BaseAgent
from fastmcp_agents.core.agents.task import TaskAgent
from fastmcp_agents.core.completions.auto import auto_llm
from fastmcp_agents.core.completions.base import LLMCompletionsProtocol
from fastmcp_agents.core.observability.logging import setup_logging


class FastMCPAgents(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    name: str = Field(default="FastMCPAgents")

    mcp: MCPConfig | dict[str, MCPServerTypes] | dict[str, Any] | None = Field(default=None)

    agents: Sequence[TaskAgent | BaseAgent] = Field(default_factory=Sequence[BaseAgent], description="The Agents to add to the server.")

    tools: dict[str, ToolTransformConfig] = Field(default_factory=dict, description="The tool transforms to apply.")

    include_tags: set[str] | None = Field(default=None, description="The tags to include in the server.")

    exclude_tags: set[str] | None = Field(default=None, description="The tags to exclude from the server.")

    llm_completions: LLMCompletionsProtocol | None = Field(default_factory=auto_llm)

    @property
    def mcp_config(self) -> MCPConfig | None:
        """Validate the MCP config."""

        if self.mcp is None:
            return None

        if isinstance(self.mcp, dict):
            return MCPConfig.model_validate(self.mcp)

        return self.mcp

    def to_server(self) -> FastMCP[Any]:
        """Convert the FastMCPAgents instance to a FastMCP server."""

        server: FastMCP[Any] = FastMCP[Any](
            name=self.name,
            include_tags=self.include_tags,
            exclude_tags=self.exclude_tags,
            tool_transformations=self.tools,
        )

        if mcp_config := self.mcp_config:
            mount_mcp_config_into_server(server=server, config=mcp_config, name_as_prefix=False)

        for agent in self.agents:
            _ = server.add_tool(tool=agent.to_tool())

        setup_logging()

        return server

    def to_client(self) -> Client[Any]:
        """Convert the FastMCPAgents instance to a FastMCP client."""

        return Client[Any](transport=self.to_server())

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> Self:
        """Convert a YAML file to a FastMCP Agents server."""

        obj: Any = yaml.safe_load(yaml_path.read_text())  # pyright: ignore[reportAny]

        return cls.model_validate(obj)
