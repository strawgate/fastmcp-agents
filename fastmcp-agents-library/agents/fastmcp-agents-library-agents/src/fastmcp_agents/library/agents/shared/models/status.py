from pydantic import BaseModel, Field


class Failure(BaseModel):
    """A Failure model for when an agent fails to complete its task."""

    reason: str = Field(description="The reason the agent failed to complete its task.")
