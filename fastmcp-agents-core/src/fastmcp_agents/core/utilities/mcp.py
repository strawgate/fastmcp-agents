from fastmcp.tools.tool import ToolResult
from mcp.types import CallToolResult, TextContent


def get_list_str_from_tool_result(tool_result: CallToolResult | ToolResult) -> list[str]:
    """Get the text from a tool result."""

    return [block.text for block in tool_result.content if isinstance(block, TextContent)]


def get_text_from_tool_result(tool_result: CallToolResult | ToolResult) -> str:
    """Get the text from a tool result."""

    return "\n".join(get_list_str_from_tool_result(tool_result))
