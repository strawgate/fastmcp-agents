"""Functions for transforming tools."""

from typing import Annotated

from fastmcp.tools.tool import FunctionTool
from fastmcp.tools.tool import Tool as FastMCPTool
from fastmcp.utilities.logging import get_logger

from fastmcp_agents.vendored.tool_transformer.models import (
    PostToolCallHookProtocol,
    PreToolCallHookProtocol,
    ToolOverride,
    ToolParameterTypes,
)

logger = get_logger(__name__)


def transform_tool(
    tool: FastMCPTool,
    override: Annotated[ToolOverride, "Tool overrides for the tool."] | None = None,
    *,
    name: Annotated[str, "The name for the transformed tool."] | None = None,
    description: Annotated[str, "The description for the transformed tool."] | None = None,
    parameter_overrides: Annotated[list[ToolParameterTypes], "Parameter overrides for the tool."] | None = None,
    hook_parameters: Annotated[list[ToolParameterTypes], "Hook parameters for the tool."] | None = None,
    pre_call_hook: Annotated[
        PreToolCallHookProtocol | None,
        "A hook that is called before a tool call is made.",
    ] = None,
    post_call_hook: Annotated[
        PostToolCallHookProtocol | None,
        "A hook that is called after a tool call is made.",
    ] = None,
) -> FunctionTool:
    """
    Transforms a tool with the given overrides.

    Args:
        tool: The tool to transform.
        override: The overrides to apply to the tool. If not provided, the name, description, parameter_overrides,
                  hook_parameters, pre_call_hook, and post_call_hook will be used.
        name: The name for the transformed tool.
        description: The description for the transformed tool.
        parameter_overrides: The parameter overrides to apply to the tool.
        hook_parameters: The hook parameters to apply to the tool.
        pre_call_hook: The pre-call hook to apply to the tool.
        post_call_hook: The post-call hook to apply to the tool.

    Returns:
        The transformed tool.

    Examples:
        >>> transform_tool(
        ...     tool=Tool(
        ...         name="my_tool",
        ...         description="This is my tool",
        ...         parameters={"arg1": "string"},
        ...     ),
        ...     name="my_tool_with_overrides",
        ...     description="This is my tool with overrides",
        ...     parameter_overrides=[
        ...         ToolParameter(
        ...             name="arg1",
        ...             description="now it has a description",
        ...             default="now it has a default value",
        ...         ),
        ...     ],
        ... )
    """

    if not override:
        override = ToolOverride(
            name=name,
            description=description,
            parameter_overrides=parameter_overrides or [],
            hook_parameters=hook_parameters or [],
            pre_call_hook=pre_call_hook,
            post_call_hook=post_call_hook,
        )

    return override.apply_to_tool(tool)
