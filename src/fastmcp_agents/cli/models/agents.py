from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
from pydantic import Field

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.llm_link.litellm import LitellmLLMLink
from fastmcp_agents.util.base_model import StrictBaseModel
from fastmcp_agents.util.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("agent.loader")


# class ReferencedAgentModel(BaseStrictModel):
#     """A model for an agent."""

#     type: Literal["loaded"] = Field(default="loaded")
#     """The type of agent."""

#     name: str = Field(...)
#     """The name of the agent."""

#     config: str = Field(...)
#     """The config file to use for the agent."""


class AgentModel(StrictBaseModel):
    """A model for an agent."""

    type: Literal["fastmcp"] = Field(default="fastmcp")
    """The type of agent."""

    name: str = Field(...)
    """The name of the agent."""

    description: list[str] | str = Field(...)
    """The description of the agent."""

    instructions: list[str] | str = Field(...)
    """The default instructions to provide to the agent."""

    # mandatory_tools: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # """A dictionary of tools the Agent must call along with their arguments."""

    allowed_tools: list[str] | None = Field(default=None)
    """An optional list of the tools to provide to the agent."""

    blocked_tools: list[str] | None = Field(default=None)
    """An optional list of the tools to block from the agent."""

    async def activate(self, fastmcp_server: FastMCP[Any]) -> CuratorAgent:
        """Activate the agent."""

        agent_tools = list((await fastmcp_server.get_tools()).values())

        if self.allowed_tools:
            agent_tools = [tool for tool in agent_tools if tool.name in self.allowed_tools]

        if self.blocked_tools:
            agent_tools = [tool for tool in agent_tools if tool.name not in self.blocked_tools]

        agent_instructions = self.instructions if isinstance(self.instructions, str) else "\n".join(self.instructions)

        agent_description = self.description if isinstance(self.description, str) else "\n".join(self.description)

        agent = CuratorAgent(
            name=self.name,
            description=agent_description,
            instructions=agent_instructions,
            default_tools=agent_tools,
            llm_link=LitellmLLMLink(),
        )

        fastmcp_server.add_tool(
            FunctionTool.from_function(
                fn=agent.perform_task,
                name=agent.name,
                description=agent.description,
                tags={"agent"},
            )
        )

        return agent
