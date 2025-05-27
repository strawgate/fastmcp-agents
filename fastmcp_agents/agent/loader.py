from pathlib import Path
from typing import Any, Literal

import yaml
from fastmcp.contrib.tool_transformer.loader import ToolOverride, ToolOverrides
from fastmcp.tools import Tool as FastMCPTool
from fastmcp.utilities.mcp_config import MCPConfig, RemoteMCPServer, StdioMCPServer
from pydantic import BaseModel, Field

from fastmcp_agents.agent import FastMCPAgent
from fastmcp_agents.agent.errors.loader import ToolsNotFoundError
from fastmcp_agents.agent.llm_link.lltellm import AsyncLitellmLLMLink
from fastmcp_agents.agent.memory.ephemeral import EphemeralMemory
from fastmcp_agents.agent.observability.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("agent.loader")


class ContentTool(BaseModel):
    """A set of overrides for a tool."""

    name: str | None = None
    description: str | None = None
    returns: str


class ContentTools(BaseModel):
    """A set of content tools."""

    tools: dict[str, ContentTool] = Field(default_factory=dict)


class ExtraToolsAndOverrides(BaseModel):
    """A set of overrides for a tool."""

    tools: dict[str, ToolOverride | ContentTool] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, string: str) -> "ExtraToolsAndOverrides":
        as_dict = yaml.safe_load(string)
        return cls.model_validate(as_dict)

    @classmethod
    def from_yaml_file(cls, path: Path) -> "ExtraToolsAndOverrides":
        with path.open("r") as f:
            return cls.model_validate(**yaml.safe_load(f))

    def get_content_tools(self) -> ContentTools:
        return ContentTools(tools={name: tool for name, tool in self.tools.items() if isinstance(tool, ContentTool)})

    def get_tool_overrides(self) -> ToolOverrides:
        return ToolOverrides(tools={name: tool for name, tool in self.tools.items() if isinstance(tool, ToolOverride)})


class StdioMCPServerWithOverrides(StdioMCPServer, ExtraToolsAndOverrides):
    pass


class RemoteMCPServerWithOverrides(RemoteMCPServer, ExtraToolsAndOverrides):
    pass


class MCPConfigWithOverrides(MCPConfig):
    mcpServers: dict[str, StdioMCPServerWithOverrides | RemoteMCPServerWithOverrides]  # type: ignore # noqa: N815

    @classmethod
    def from_dict(cls, config: dict[str, Any]):
        return cls(mcpServers=config.get("mcpServers", config))


class AgentConfig(BaseModel):
    type: Literal["fastmcp"] = "fastmcp"
    name: str = Field(..., description="The name of the agent.")
    description: str = Field(..., description="The description of the agent.")
    default_instructions: str = Field(..., description="The default instructions to provide to the agent.")
    model: str | None = Field(default=None, description="The model to use for the agent.")
    allowed_tools: list[str] | None = Field(None, description="The optional names of the tools to provide to the agent.")
    blocked_tools: list[str] | None = Field(None, description="The optional names of the tools to block from the agent.")


class AgentsConfig(BaseModel):
    agents: list[AgentConfig] = Field(..., description="The list of agents to load.")

    @classmethod
    def from_yaml_file(cls, path: Path) -> "AgentsConfig":
        with path.open("r", encoding="utf-8") as f:
            as_dict = yaml.safe_load(f)
            return cls.model_validate(as_dict)


class Config(AgentsConfig, MCPConfigWithOverrides):
    pass


def load_agent(agent_config: AgentConfig, default_model: str, tools: list[FastMCPTool]) -> FastMCPAgent:
    logger.info("Loading agent %s with model %s", agent_config.name, agent_config.model or default_model)

    llm_link = AsyncLitellmLLMLink.from_model(model=agent_config.model or default_model)

    agent_tools = list(tools)

    if agent_config.allowed_tools:
        agent_tools = [tool for tool in agent_tools if tool.name in agent_config.allowed_tools]

        missing_tools = set(agent_config.allowed_tools) - set(tool.name for tool in agent_tools)

        if missing_tools:
            raise ToolsNotFoundError(agent_config.name, missing_tools)

    if agent_config.blocked_tools:
        agent_tools = [tool for tool in agent_tools if tool.name not in agent_config.blocked_tools]

    logger.info("Agent %s will have access to the following tools: %s", agent_config.name, [tool.name for tool in agent_tools])

    return FastMCPAgent(
        name=agent_config.name,
        description=agent_config.description,
        default_instructions=agent_config.default_instructions,
        llm_link=llm_link,
        tools=agent_tools,
        memory=EphemeralMemory(),
    )


def load_agents(agent_configs: list[AgentConfig], default_model: str, tools: list[FastMCPTool]) -> list[FastMCPAgent]:
    return [load_agent(agent_config, default_model, tools) for agent_config in agent_configs]
