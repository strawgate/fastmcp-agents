"""Tools for redirecting tool calls."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastmcp import Context
from mcp.types import EmbeddedResource, ImageContent, TextContent


async def redirect_to_tool_call(
    ctx: Context,
    first_tool_name: str,
    first_tool_arguments: dict[str, Any],
    second_tool_name: str,
    second_tool_arguments: dict[str, Any],
    second_tool_response_argument: str,
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Redirect the result of any existing tool call to another tool call.

    Args:
        first_tool_name: The name of the first tool to call.
        first_tool_arguments: The arguments to pass to the first tool.
        second_tool_name: The name of the second tool to call.
        second_tool_arguments: The arguments to pass to the second tool.
        second_tool_response_argument: The name of the argument to insert the result of the first tool call into.

    Returns:
        A list of content from the second tool call.
    """

    tools = await ctx.fastmcp.get_tools()
    first_tool = tools[first_tool_name]
    second_tool = tools[second_tool_name]

    first_tool_result = await first_tool.run(first_tool_arguments)

    second_tool_full_arguments = deepcopy(second_tool_arguments)
    second_tool_full_arguments[second_tool_response_argument] = first_tool_result
    return await second_tool.run(second_tool_full_arguments)


async def redirect_to_file(ctx: Context, tool_name: str, arguments: dict, path: Path) -> bool:
    """Redirect any tool call to a local file.

    This is useful for debugging tools that are not available in the local environment.

    Args:
        tool_name: The name of the tool to redirect.
        arguments: The arguments to pass to the tool.
        path: The path to the file to write the tool call result to.

    Returns:
        True if the tool call was successful, False otherwise.
    """

    tools = await ctx.fastmcp.get_tools()
    tool = tools[tool_name]

    tool_call_result = await tool.run(arguments)

    with Path(path).open("w", encoding="utf-8") as f:
        f.write(json.dumps(tool_call_result, indent=2))

    return True
