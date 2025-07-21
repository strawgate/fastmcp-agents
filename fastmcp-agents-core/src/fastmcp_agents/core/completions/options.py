import os
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class CompletionSettings(BaseModel):
    """Options for the model."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True, use_attribute_docstrings=True)

    model: str | None = Field(default=None, description="The model to use for the completion.")

    temperature: float | None = Field(default=None, description="The temperature to use for the completion.")

    top_p: float | None = Field(default=None, description="The top p to use for the completion.")

    max_tokens: int | None = Field(default=None, description="The maximum number of tokens to use for the completion.")

    reasoning_effort: Literal["low", "medium", "high"] | None = Field(
        default=None, description="The effort to put into reasoning about the completion."
    )

    frequency_penalty: float | None = Field(default=None, description="The frequency penalty to use for the completion.")

    @classmethod
    def from_environment(cls) -> "CompletionSettings":
        """Create a completion options from the environment."""

        temperature = os.getenv("MODEL_TEMPERATURE")
        top_p = os.getenv("MODEL_TOP_P")
        max_tokens = os.getenv("MODEL_MAX_TOKENS")
        frequency_penalty = os.getenv("MODEL_FREQUENCY_PENALTY")
        reasoning_effort = os.getenv("MODEL_REASONING_EFFORT")

        return cls(
            model=os.getenv("MODEL"),
            temperature=float(temperature) if temperature else None,
            top_p=float(top_p) if top_p else None,
            max_tokens=int(max_tokens) if max_tokens else None,
            reasoning_effort=reasoning_effort if reasoning_effort in ["low", "medium", "high"] else None,  # pyright: ignore[reportArgumentType]
            frequency_penalty=float(frequency_penalty) if frequency_penalty else None,
        )
