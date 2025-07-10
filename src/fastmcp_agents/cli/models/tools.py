from collections.abc import Callable
from typing import Any, ClassVar, Literal, override

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
from fastmcp.tools import Tool as FastMCPTool
from fastmcp.tools.tool_transform import ArgTransform
from fastmcp.utilities.types import NotSet, NotSetT
from pydantic import BaseModel, ConfigDict, Field

from fastmcp_agents.util.base_model import LenientBaseModel, StrictBaseModel
from fastmcp_agents.util.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("agent.loader")


class BaseExtraTool(StrictBaseModel):
    """A set of overrides for a tool."""

    name: str = Field(...)
    """The name of the extra tool."""

    description: str = Field(...)
    """The description of the extra tool that is provided to the client."""

    def to_fastmcp_tool(self) -> FastMCPTool:
        msg = "Subclasses must implement this method."
        raise NotImplementedError(msg)

    async def activate(self, fastmcp_server: FastMCP[Any]) -> FastMCPTool:
        """Activate the tool."""
        tool: FastMCPTool = self.to_fastmcp_tool()

        fastmcp_server.add_tool(tool)

        return tool


class StaticStringTool(BaseExtraTool):
    """A tool that returns a static string."""

    returns: str = Field(...)
    """The string to return when the tool is called."""

    @override
    def to_fastmcp_tool(self) -> FunctionTool:
        """Convert the tool to a FastMCP tool."""

        return FunctionTool.from_function(
            fn=lambda: self.returns,
            name=self.name,
            description=self.description,
        )

class ArgumentTransform(LenientBaseModel):

    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    default: str | int | float | bool | None = Field(default=None)
    hide: bool = Field(default=False)
    required: Literal[True] | None = Field(default=None)
    examples: Any | None = Field(default=None)

    def to_arg_transform(self) -> ArgTransform:
        """Convert the argument transform to a FastMCP argument transform."""
        return ArgTransform(**self.model_dump(exclude_none=True))  # pyright: ignore[reportAny]



class ToolTransform(BaseModel):
    """Provides a way to transform a tool."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True, use_attribute_docstrings=True)

    name: str | None = Field(default=None)
    """The new name of the tool."""

    enabled: bool | None = Field(default=None)
    """Whether the tool should be enabled on the server."""

    description: str | None = Field(default=None)
    """The description of the tool. You can access the original description with `{original_description}`."""

    description_append: str | None = Field(default=None)
    """A string to append to the description of the tool."""

    parameters: dict[str, ArgumentTransform] = Field(default_factory=dict)
    """A dictionary of parameter transforms to apply to the tool."""

    def apply_to_tool(self, tool: FastMCPTool) -> FastMCPTool | None:
        """Apply the transform to the tool."""

        if self.enabled is False:
            return None

        description = self.description or tool.description
        if self.description_append:
            description = f"{description}\n\n{self.description_append}"

        return FastMCPTool.from_tool(
            tool=tool,
            name=self.name,
            description=description,
            transform_args={k: v.to_arg_transform() for k, v in self.parameters.items()},
            enabled=self.enabled,
        )


ExtraToolTypes = StaticStringTool
