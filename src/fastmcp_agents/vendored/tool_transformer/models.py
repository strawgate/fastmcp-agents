"""Pydantic models for tool transformation."""

from collections.abc import Awaitable, Callable
from copy import deepcopy
from typing import Annotated, Any, Generic, Literal, Protocol, TypeVar, runtime_checkable

from fastmcp.exceptions import ToolError
from fastmcp.tools import FunctionTool
from fastmcp.tools import Tool as FastMCPTool
from jsonschema import ValidationError, validate
from mcp.types import EmbeddedResource, ImageContent, TextContent
from pydantic import BaseModel, ConfigDict, Field, model_validator

from fastmcp_agents.vendored.tool_transformer.errors import (
    ToolParameterAlreadyExistsError,
    ToolParameterNotFoundError,
    ToolParameterOverrideError,
)

T = TypeVar("T", bound=bool | int | float | str)  # | dict[str, Any] | BaseModel)


class ToolParameter(BaseModel, Generic[T]):
    """A base class for a tool parameter."""

    name: str = Field(description="The name of the parameter.")
    description: str | None = Field(default=None, description="The description of the parameter.")
    append_description: str | None = Field(default=None, description="A description to append to the parameter's description.")
    required: bool = Field(default=False, description="Whether the parameter is required.")
    constant: T | None = Field(default=None, description="A constant value for the parameter.")
    default: T | None = Field(default=None, description="A default value for the parameter.")

    @model_validator(mode="after")
    def validate_default_and_constant(self):
        if self.default is not None and self.constant is not None:
            msg = "Cannot set both default and constant for a parameter."
            raise ToolParameterOverrideError(msg)

        return self

    @classmethod
    def _get_jsonschema_type(cls) -> str:
        msg = "Subclasses must implement this method."
        raise NotImplementedError(msg)

    def add_into_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Adds the parameter into the schema.

        Args:
            schema: The schema of the tool.

        Returns:
            The updated schema. Does not modify the schema in place.
        """

        working_schema = deepcopy(schema)

        if not working_schema.get("properties"):
            working_schema["properties"] = {}

        if self.name in working_schema["properties"]:
            raise ToolParameterAlreadyExistsError(self.name)

        new_parameter: dict[str, Any] = {
            "type": self._get_jsonschema_type(),
            "title": self.name,
        }

        if self.description is not None:
            new_parameter["description"] = self.description

        if self.default is not None:
            new_parameter["default"] = self.default

        if self.constant is not None:
            new_parameter["const"] = self.constant

        working_schema["properties"][self.name] = new_parameter

        if self.required:
            working_schema.setdefault("required", []).append(self.name)

        return working_schema

    def merge_into_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Merges the parameter into the schema.

        Args:
            schema: The schema of the tool.

        Returns:
            The updated schema. Also modifies the schema in place.
        """
        working_schema = deepcopy(schema)

        if not working_schema.get("properties"):
            working_schema["properties"] = {}

        if self.name not in working_schema["properties"]:
            raise ToolParameterNotFoundError(self.name)

        parameter_schema = working_schema["properties"][self.name]

        if parameter_schema.get("description") is not None and self.append_description is not None:
            parameter_schema["description"] += "\n" + self.append_description

        if self.description is not None:
            parameter_schema["description"] = self.description

        if self.default is not None:
            parameter_schema["default"] = self.default

        if self.constant is not None:
            parameter_schema["const"] = self.constant

        if self.required and self.name not in working_schema.get("required", []):
            working_schema.setdefault("required", []).append(self.name)

        return working_schema

    def apply_to_schema(
        self,
        schema: dict[str, Any],
        existing_parameter_behavior: Literal["error", "merge"] = "error",
    ) -> dict[str, Any]:
        """
        Applies the parameter to the schema.

        Args:
            schema: The schema of the tool.
            existing_parameter_behavior: The behavior to use when the parameter already exists in the schema.

        """

        already_in_schema = self.name in schema["properties"]

        if not already_in_schema:
            working_schema = self.add_into_schema(schema)
        else:
            if existing_parameter_behavior == "error":
                raise ToolParameterAlreadyExistsError(self.name)
            working_schema = self.merge_into_schema(schema)

        return working_schema


class IntToolParameter(ToolParameter[int]):
    """A parameter that is an integer."""

    @classmethod
    def _get_jsonschema_type(cls) -> str:
        return "number"


class FloatToolParameter(ToolParameter[float]):
    """A parameter that is a float."""

    @classmethod
    def _get_jsonschema_type(cls) -> str:
        return "number"


class StringToolParameter(ToolParameter[str]):
    """A parameter that is a string."""

    @classmethod
    def _get_jsonschema_type(cls) -> str:
        return "string"


class BooleanToolParameter(ToolParameter[bool]):
    """A parameter that is a boolean."""

    @classmethod
    def _get_jsonschema_type(cls) -> str:
        return "boolean"


# class DictToolParameter(ToolParameter[dict[str, Any]]):
#     """A parameter that is an object."""

#     type: dict[str, Any]

#     @classmethod
#     def _get_jsonschema_type(cls) -> str:
#         return "object"


# class BaseModelToolParameter(ToolParameter[BaseModel]):
#     """A parameter that is a model."""

#     type: BaseModel

#     @classmethod
#     def _get_jsonschema_type(cls) -> str:
#         return "object"


ToolParameterTypes = (
    IntToolParameter
    | FloatToolParameter
    | StringToolParameter
    | BooleanToolParameter
    # | DictToolParameter
    # | BaseModelToolParameter
    | ToolParameter
)


@runtime_checkable
class PostToolCallHookProtocol(Protocol):
    async def __call__(
        self,
        response: list[TextContent | ImageContent | EmbeddedResource],
        tool_args: dict[str, Any],
        hook_args: dict[str, Any],
    ) -> None: ...


@runtime_checkable
class PreToolCallHookProtocol(Protocol):
    async def __call__(
        self,
        tool_args: dict[str, Any],
        hook_args: dict[str, Any],
    ) -> None: ...


HookProtocolTypes = PreToolCallHookProtocol | PostToolCallHookProtocol


class ToolOverride(BaseModel):
    """A base class for a tool override that can be used to override a tool."""

    name: str | None = Field(default=None, description="The name of the tool to override.")
    description: str | None = Field(default=None, description="The description of the tool to override.")
    append_description: str | None = Field(default=None, description="A description to append to the tool's description.")
    parameter_overrides: list[ToolParameterTypes] = Field(
        default_factory=list,
        description="A list of parameter overrides to apply to the tool.",
    )
    hook_parameters: list[ToolParameterTypes] = Field(
        default_factory=list,
        description="A list of hook parameters to apply to the tool.",
    )
    pre_call_hook: PreToolCallHookProtocol | None = Field(
        default=None,
        description="A hook to call before the tool is called.",
        exclude=True,
    )
    post_call_hook: PostToolCallHookProtocol | None = Field(
        default=None,
        description="A hook to call after the tool is called.",
        exclude=True,
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def apply_to_tool(
        self,
        tool: FastMCPTool,
    ) -> FunctionTool:
        return _transform_tool(tool, self)


def _extract_hook_args(
    extra_parameters: list[ToolParameterTypes],
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
    hook_parameters: list[ToolParameterTypes],
) -> dict[str, Any]:
    """Applies extra parameters for hooks to the tool parameters schema."""
    transformed_schema = deepcopy(schema)

    for hook_parameter in hook_parameters:
        transformed_schema = hook_parameter.add_into_schema(transformed_schema)

    return transformed_schema


def _apply_parameter_overrides(
    schema: dict[str, Any],
    overrides: list[ToolParameterTypes],
) -> dict[str, Any]:
    """
    Applies parameter overrides to a schema.
    """
    transformed_schema = deepcopy(schema)

    for override in overrides:
        transformed_schema = override.merge_into_schema(transformed_schema)

    return transformed_schema


def _create_transformed_function(
    original_tool_run_method: Callable[..., Awaitable[list[TextContent | ImageContent | EmbeddedResource]]],
    fn_transformed_parameters_schema: dict[str, Any],
    fn_hook_parameters_list: list[ToolParameterTypes],
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


def _transform_tool(
    tool: FastMCPTool,
    override: Annotated[ToolOverride, "Tool overrides for the tool."],
) -> FunctionTool:
    transformed_parameters: dict[str, Any] = deepcopy(tool.parameters)

    transformed_parameters = _apply_hook_parameters(schema=transformed_parameters, hook_parameters=override.hook_parameters)
    transformed_parameters = _apply_parameter_overrides(schema=transformed_parameters, overrides=override.parameter_overrides)

    transformed_fn_callable = _create_transformed_function(
        original_tool_run_method=tool.run,
        fn_transformed_parameters_schema=transformed_parameters,
        fn_hook_parameters_list=override.hook_parameters,
        fn_pre_call_hook=override.pre_call_hook,
        fn_post_call_hook=override.post_call_hook,
    )

    transformed_name: str = override.name or tool.name
    transformed_description: str | None = tool.description

    if transformed_description and override.append_description is not None:
        transformed_description += "\n" + override.append_description

    if override.description is not None:
        transformed_description = override.description

    return FunctionTool(
        fn=transformed_fn_callable,
        name=transformed_name,
        description=transformed_description,
        parameters=transformed_parameters,
        tags=tool.tags,
        annotations=tool.annotations,
        serializer=tool.serializer,
        exclude_args=tool.exclude_args,
    )
