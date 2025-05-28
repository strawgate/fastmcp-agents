from collections.abc import Awaitable, Callable
from copy import deepcopy
from typing import Annotated, Any

from fastmcp.exceptions import ToolError
from fastmcp.server.server import FastMCP
from fastmcp.tools.tool import Tool as FastMCPTool
from fastmcp.utilities.logging import get_logger
from jsonschema import ValidationError, validate
from mcp.types import EmbeddedResource, ImageContent, TextContent

from fastmcp_agents.tool_transformer.types import (
    ExtraToolParameterTypes,
    PostToolCallHookProtocol,
    PreToolCallHookProtocol,
    ToolParameterOverride,
)

logger = get_logger(__name__)


def _extract_hook_args(
    extra_parameters: list[ExtraToolParameterTypes],
    tool_call_kwargs: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Extracts the hook arguments from the tool call kwargs.
    """
    hook_args: dict[str, Any] = {}
    tool_call_args: dict[str, Any] = deepcopy(tool_call_kwargs)

    extra_parameters_by_name = {extra_parameter.name: extra_parameter for extra_parameter in extra_parameters}

    for tool_arg_name in tool_call_kwargs:
        if tool_arg_name in extra_parameters_by_name:
            hook_args[tool_arg_name] = tool_call_args.pop(tool_arg_name)

    return hook_args, tool_call_args


def _apply_hook_parameters(
    schema: dict[str, Any],
    hook_parameters: list[ExtraToolParameterTypes],
) -> dict[str, Any]:
    """Applies extra parameters for hooks to the tool parameters schema."""
    transformed_schema = deepcopy(schema)

    for hook_parameter in hook_parameters:
        transformed_schema = hook_parameter.combine_into_schema(transformed_schema)

    return transformed_schema


def _apply_parameter_overrides(
    schema: dict[str, Any],
    parameter_overrides: dict[str, ToolParameterOverride],
) -> dict[str, Any]:
    """
    Applies parameter overrides to a schema.
    """
    transformed_schema = deepcopy(schema)

    for param_name, param_override in parameter_overrides.items():
        transformed_schema = param_override.combine_into_schema(param_name, transformed_schema)

    for param_name, param_schema in transformed_schema.get("properties", {}).items():
        # Bug in LiteLLM means we need to remove descriptions of fields with
        # anyOf present
        if param_name == "description":
            pass
        if "anyOf" in param_schema and "description" in param_schema:
            logger.warning(f"Removing description for {param_name} because of anyOf")
            del param_schema["description"]

        if "anyOf" in param_schema and "default" in param_schema:
            logger.warning(f"Removing default for {param_name} because of anyOf")
            del param_schema["default"]

    return transformed_schema


def _create_transformed_function(
    original_tool_run_method: Callable[..., Awaitable[list[TextContent | ImageContent | EmbeddedResource]]],
    fn_transformed_parameters_schema: dict[str, Any],
    fn_hook_parameters_list: list[ExtraToolParameterTypes],
    fn_pre_call_hook: PreToolCallHookProtocol | None,
    fn_post_call_hook: PostToolCallHookProtocol | None,
) -> Callable[..., Awaitable[list[TextContent | ImageContent | EmbeddedResource]]]:
    """Factory function to create the transformed tool's core async callable."""

    async def transformed_fn(
        **kwargs: Any,
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        try:
            validate(kwargs, fn_transformed_parameters_schema)
        except ValidationError as e:
            msg = f"Provided arguments for {e.json_path} are invalid: {e.message}"
            raise ToolError(msg) from e

        hook_args, tool_call_kwargs = _extract_hook_args(fn_hook_parameters_list, kwargs)

        if fn_pre_call_hook:
            await fn_pre_call_hook(tool_call_kwargs, hook_args)

        response = await original_tool_run_method(arguments=tool_call_kwargs)

        if fn_post_call_hook:
            await fn_post_call_hook(response, tool_call_kwargs, hook_args)

        return response

    return transformed_fn


def transform_tool(
    tool: FastMCPTool,
    add_to_server: FastMCP,
    *,
    name: Annotated[str | None, "The name for the transformed tool."] = None,
    description: Annotated[str | None, "The description for the transformed tool."] = None,
    hook_parameters: Annotated[
        list[ExtraToolParameterTypes],
        "Extra parameters that the caller will have to provide that will be passed to the hook.",
    ]
    | None = None,
    parameter_overrides: Annotated[dict[str, ToolParameterOverride], "Parameter overrides for the tool."] | None = None,
    pre_call_hook: Annotated[
        PreToolCallHookProtocol | None,
        "A hook that is called before a tool call is made.",
    ] = None,
    post_call_hook: Annotated[
        PostToolCallHookProtocol | None,
        "A hook that is called after a tool call is made.",
    ] = None,
) -> FastMCPTool:
    if not hook_parameters:
        hook_parameters = []

    if not parameter_overrides:
        parameter_overrides = {}

    # Handle parameter transformations by calling the new helper function
    transformed_parameters = _apply_hook_parameters(schema=tool.parameters, hook_parameters=hook_parameters)

    transformed_parameters = _apply_parameter_overrides(
        schema=transformed_parameters,
        parameter_overrides=parameter_overrides,
    )

    transformed_name = name or tool.name
    transformed_description = description or tool.description

    transformed_fn_callable = _create_transformed_function(
        original_tool_run_method=tool.run,
        fn_transformed_parameters_schema=transformed_parameters,
        fn_hook_parameters_list=hook_parameters,
        fn_pre_call_hook=pre_call_hook,
        fn_post_call_hook=post_call_hook,
    )

    transformed_tool = FastMCPTool(
        fn=transformed_fn_callable,
        name=transformed_name,
        description=transformed_description,
        parameters=transformed_parameters,
        tags=tool.tags,
        annotations=tool.annotations,
        serializer=tool.serializer,
    )

    add_to_server._tool_manager.add_tool(transformed_tool)

    return transformed_tool
