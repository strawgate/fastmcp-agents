"""Utility functions for conversation handling."""

from mcp.types import BlobResourceContents, EmbeddedResource, ImageContent, TextContent, TextResourceContents


def join_content(content: list[TextContent | ImageContent | EmbeddedResource]) -> str:
    """Join the content of a list of TextContent, ImageContent, or EmbeddedResource into a single string.

    Args:
        content: The list of content to join.

    Returns:
        A string of the joined content.
    """

    result = ""

    for item in content:
        if isinstance(item, TextContent):
            result += item.text
        elif isinstance(item, ImageContent):
            result += f"an image {item.mimeType}"
        elif isinstance(item, BlobResourceContents):
            result += f"a blob {item.mimeType}"
        elif isinstance(item, TextResourceContents):
            result += f"a text resource {item.text}"
        elif isinstance(item, EmbeddedResource):
            result += f"an embedded resource {item.type}"

    return result
