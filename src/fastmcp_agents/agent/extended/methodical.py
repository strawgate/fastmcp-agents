"""A methodical agent that uses the tools available on the server to complete a requested task."""

from pydantic import BaseModel, Field

from fastmcp_agents.agent.curator import CuratorAgent
from fastmcp_agents.agent.multi_step import DefaultErrorResponseModel, DefaultSuccessResponseModel
from fastmcp_agents.conversation.types import Conversation


class MethodicalStep(BaseModel):
    """A step in the methodical plan."""

    id: int = Field(..., description="The id of the step.")
    step: str = Field(..., description="The step to perform.")


class MethodicalPlan(BaseModel):
    """A methodical plan."""

    steps: list[MethodicalStep] = Field(..., description="The steps to perform.")


class Fact(BaseModel):
    """A fact discovered during the methodical process of completing a task."""

    fact: str = Field(..., description="The fact discovered.")
    source: str = Field(..., description="The source of the fact.")


class MethodicalAgent(CuratorAgent):
    """A methodical agent that uses the tools available on the server to complete a requested task."""

    async def run_steps(
        self,
        *args,
        **kwargs,
    ) -> tuple[Conversation, DefaultSuccessResponseModel | DefaultErrorResponseModel]:
        """Run the steps of the agent."""
        return await super().run_steps(*args, **kwargs)
