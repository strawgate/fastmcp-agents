from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    """A base model for all FastMCP Agents models that are strict."""

    model_config: ClassVar[ConfigDict] = ConfigDict(use_attribute_docstrings=True, frozen=True, strict=True, extra="forbid")


class LenientBaseModel(BaseModel):
    """A base model for all FastMCP Agents models that are lenient."""

    model_config: ClassVar[ConfigDict] = ConfigDict(use_attribute_docstrings=True, frozen=True, arbitrary_types_allowed=True)
