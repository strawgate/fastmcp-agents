from typing import Any

from mcp.types import Tool
from rich import box
from rich.table import Table

MAX_TOOL_DESCRIPTION_LENGTH = 400
MAX_TOOL_ARGUMENT_DESCRIPTION_LENGTH = 100


def rich_table_from_tools(tools: list[Tool]) -> Table:
    """Create a rich table from a list of tools."""
    table = Table(title="Tools", highlight=True, padding=(1, 1), show_lines=True, box=box.ROUNDED)

    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Arguments")

    for tool in tools:
        tool_name: str = tool.name

        tool_description: str = tool.description or "<none>"

        if len(tool_description) > MAX_TOOL_DESCRIPTION_LENGTH:
            tool_description = tool_description[:MAX_TOOL_DESCRIPTION_LENGTH] + "... (truncated)"

        if not tool.inputSchema:
            table.add_row(tool_name, tool_description, "<none>")
            continue

        schema_properties: dict[str, Any] | None = tool.inputSchema.get("properties")

        if not schema_properties:
            table.add_row(tool_name, tool_description, "<none>")
            continue

        arguments_table = Table(show_header=False, show_edge=False, show_lines=True, box=box.HORIZONTALS)
        arguments_table.add_column("Name")
        arguments_table.add_column("Description")

        for argument, definition in schema_properties.items():  # pyright: ignore[reportAny]
            if not isinstance(definition, dict):
                continue

            argument_description: str | None = None
            argument_type: str | None = None

            for key, value in definition.items():  # pyright: ignore[reportUnknownVariableType]
                if key == "description" and isinstance(value, str):
                    argument_description = value

                    if len(argument_description) > MAX_TOOL_ARGUMENT_DESCRIPTION_LENGTH:
                        argument_description = argument_description[:MAX_TOOL_ARGUMENT_DESCRIPTION_LENGTH] + "... (truncated)"

                if key == "type" and isinstance(value, str):
                    argument_type = value

            arguments_table.add_row(f"{argument}\n({argument_type})", argument_description)

        table.add_row(tool.name, tool_description, arguments_table)

    return table
