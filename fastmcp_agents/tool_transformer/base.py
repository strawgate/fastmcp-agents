from typing import Any

from pydantic import BaseModel, Field, model_validator


class TransformedToolError(Exception):
    """An error that occurs when a tool is transformed."""

    def __init__(self, message: str):
        super().__init__(message)


class ToolParameterOverrideError(TransformedToolError):
    """An error that occurs when a parameter override is invalid."""

    def __init__(self, parameter_name: str):
        super().__init__(f"Parameter {parameter_name} not found in tool.")


class BaseExtraToolParameter(BaseModel):
    """A base class for adding extra parameters to a tool."""

    type: str = Field(description="The type of the extra parameter.")
    name: str = Field(description="The name of the extra parameter.")
    description: str = Field(description="The description of the extra parameter.")
    required: bool = Field(description="Whether the extra parameter is required.")
    default: bool | int | float | str | None = Field(
        default=None, description="A default value for the extra parameter."
    )

    def combine_into_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Combines the extra parameter into the schema.

        Args:
            schema: The schema of the tool.

        Returns:
            The updated schema. Also modifies the schema in place.
        """
        if not schema:
            schema = {}

        if not schema.get("properties"):
            schema["properties"] = {}

        schema["properties"][self.name] = {
            "type": self.type,
            "title": self.name,
            "description": self.description,
            "default": self.default,
        }

        if self.required:
            schema.setdefault("required", []).append(self.name)

        return schema


class BaseToolParameterOverride(BaseModel):
    """A parameter override for a tool."""

    description: str | None = Field(
        default=None, description="The new description for the parameter."
    )
    constant: bool | int | float | str | None = Field(
        default=None, description="The constant value to use for the parameter."
    )
    default: bool | int | float | str | None = Field(
        default=None, description="The new default value to use for the parameter."
    )
    required: bool | None = Field(
        default=None,
        description="Whether to make the parameter required. A required parameter cannot be made optional.",
    )

    @model_validator(mode="after")
    def validate_default_and_constant(self):
        if self.default is not None and self.constant is not None:
            raise ToolParameterOverrideError(
                "Cannot set both default and constant for a parameter."
            )

        return self

    def combine_into_schema(
        self, parameter_name: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Combines the parameter override into the schema.

        Args:
            existing_parameter_name: The name of the existing parameter.
            schema: The schema of the tool.

        Returns:
            The updated schema. Also modifies the schema in place.
        """

        # We can only override parameters that exist
        if parameter_name not in schema["properties"]:
            raise ToolParameterOverrideError(parameter_name=parameter_name)

        existing_parameter = schema["properties"][parameter_name]

        # We can override the name of a parameter
        if self.description is not None:
            existing_parameter["description"] = self.description

        # We can force a parameter to have a constant value
        if self.constant is not None:
            existing_parameter["const"] = self.constant

        # We can override the default value of a parameter
        if self.default is not None:
            existing_parameter["default"] = self.default

        # We cannot make a required parameter optional, but we can make an optional parameter required
        is_already_required = parameter_name in schema.get("required", [])

        should_be_made_required = self.required is not None and self.required is True

        if should_be_made_required and not is_already_required:
            schema.setdefault("required", []).append(parameter_name)

        return schema
