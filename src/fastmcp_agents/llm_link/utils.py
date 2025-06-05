"""Utility functions for LLM link."""

from copy import deepcopy

from fastmcp.tools import Tool as FastMCPTool
from openai.types.chat import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition


def transform_fastmcp_tool_to_openai_tool(fastmcp_tool: FastMCPTool) -> ChatCompletionToolParam:
    """Convert an FastMCP tool to an OpenAI tool."""

    tool_name = fastmcp_tool.name
    tool_description = fastmcp_tool.description or ""
    tool_parameters = deepcopy(fastmcp_tool.parameters)

    return ChatCompletionToolParam(
        type="function",
        function=FunctionDefinition(
            name=tool_name,
            description=tool_description,
            parameters=tool_parameters,
            strict=False,
        ),
    )
