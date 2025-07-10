from typing import Any

import pytest
from fastmcp.tools import Tool as FastMCPTool
from mcp.types import TextContent

from fastmcp_agents.cli.models.tools import ArgumentTransform, StaticStringTool, ToolTransform


@pytest.fixture
def fastmcp_tool():
    """A fixture for a FastMCP tool."""

    def fn(param1: str, param2: str) -> str:  # noqa: ARG001
        return "test"

    return FastMCPTool.from_function(fn=fn, name="test tool", description="test tool description")


def test_init():
    """Test the ToolTransform model."""

    transform = ToolTransform(name="name other than test", description="description other than test")

    assert transform.name == "name other than test"
    assert transform.description == "description other than test"


def test_transform_display(fastmcp_tool: FastMCPTool):
    """Test the ToolTransform model."""

    transform = ToolTransform(name="name other than test", description="description other than test")

    assert transform.name == "name other than test"
    assert transform.description == "description other than test"

    transformed_tool = transform.apply_to_tool(tool=fastmcp_tool)

    assert transformed_tool is not None
    assert transformed_tool.name == "name other than test"
    assert transformed_tool.description == "description other than test"


def test_transform_parameter_name_description(fastmcp_tool: FastMCPTool):
    """Test the ToolTransform model."""

    transform = ToolTransform(
        parameters={
            "param1": ArgumentTransform(name="new_name_1"),
            "param2": ArgumentTransform(description="new description 2"),
        }
    )

    transformed_tool = transform.apply_to_tool(tool=fastmcp_tool)

    assert transformed_tool is not None
    properties: dict[str, Any] = transformed_tool.parameters["properties"]
    assert "new_name_1" in properties
    assert "description" not in properties["new_name_1"]

    assert "param2" in properties
    assert properties["param2"]["description"] == "new description 2"


def test_transform_parameter_defaults(fastmcp_tool: FastMCPTool):
    """Test the ToolTransform model."""

    transform = ToolTransform(
        parameters={
            "param1": ArgumentTransform(default="default value 1"),
        }
    )

    transformed_tool = transform.apply_to_tool(tool=fastmcp_tool)

    assert transformed_tool is not None
    properties = transformed_tool.parameters["properties"]
    assert "param1" in properties
    assert properties["param1"]["default"] == "default value 1"


def test_transform_parameter_hide(fastmcp_tool: FastMCPTool):
    """Test the ToolTransform model."""

    transform = ToolTransform(
        parameters={
            "param1": ArgumentTransform(hide=True, default="default value 1"),
        }
    )

    transformed_tool = transform.apply_to_tool(tool=fastmcp_tool)

    assert transformed_tool is not None
    properties = transformed_tool.parameters["properties"]
    assert "param1" not in properties


async def test_static_string_tool():
    """Test the StaticStringTool model."""

    tool = StaticStringTool(name="test tool", description="test tool description", returns="test")

    fastmcp_tool = tool.to_fastmcp_tool()

    assert fastmcp_tool.name == "test tool"
    assert fastmcp_tool.description == "test tool description"

    result = await fastmcp_tool.run(arguments={})

    first_text_result = result.content[0]
    assert isinstance(first_text_result, TextContent)

    assert first_text_result.text == "test"
