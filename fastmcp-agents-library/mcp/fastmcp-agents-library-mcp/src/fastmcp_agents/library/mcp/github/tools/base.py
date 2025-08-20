from fastmcp.tools.tool_transform import ToolTransformConfig


def get_scope_tag(tool_config: ToolTransformConfig) -> str:
    scope_tag: str | None = next((tag.split(":")[1] for tag in tool_config.tags if tag.startswith("scope:")), None)

    if scope_tag is None:
        msg = f"Scope tag not found for tool {tool_config.name}"
        raise ValueError(msg)

    return scope_tag


def get_verb_tag(tool_config: ToolTransformConfig) -> str:
    verb_tag: str | None = next((tag.split(":")[1] for tag in tool_config.tags if tag.startswith("verb:")), None)

    if verb_tag is None:
        msg = f"Verb tag not found for tool {tool_config.name}"
        raise ValueError(msg)

    return verb_tag


def get_object_tag(tool_config: ToolTransformConfig) -> str:
    object_tag: str | None = next((tag.split(":")[1] for tag in tool_config.tags if tag.startswith("object:")), None)

    if object_tag is None:
        msg = f"Object tag not found for tool {tool_config.name}"
        raise ValueError(msg)

    return object_tag


def get_tool_tag(tool_config: ToolTransformConfig) -> tuple[str, str, str]:
    return get_scope_tag(tool_config), get_verb_tag(tool_config), get_object_tag(tool_config)


def get_unique_scopes(tools: dict[str, ToolTransformConfig]) -> set[str]:
    return {get_scope_tag(tool) for tool in tools.values()}


def get_unique_verbs(tools: dict[str, ToolTransformConfig]) -> set[str]:
    return {get_verb_tag(tool) for tool in tools.values()}


def get_unique_objects(tools: dict[str, ToolTransformConfig]) -> set[str]:
    return {get_object_tag(tool) for tool in tools.values()}


def filter_tools(
    tools: dict[str, ToolTransformConfig],
    allowed_scopes: set[str] | None = None,
    allowed_verbs: set[str] | None = None,
    allowed_objects: set[str] | None = None,
    blocked_scopes: set[str] | None = None,
    blocked_verbs: set[str] | None = None,
    blocked_objects: set[str] | None = None,
    required_arguments: set[str] | None = None,
) -> dict[str, ToolTransformConfig]:
    """Filter tools by scope, verb, and object."""

    return {
        tool_name: tool_config
        for tool_name, tool_config in tools.items()
        if (allowed_scopes is None or get_scope_tag(tool_config) in allowed_scopes)
        and (allowed_verbs is None or get_verb_tag(tool_config) in allowed_verbs)
        and (allowed_objects is None or get_object_tag(tool_config) in allowed_objects)
        and (blocked_scopes is None or get_scope_tag(tool_config) not in blocked_scopes)
        and (blocked_verbs is None or get_verb_tag(tool_config) not in blocked_verbs)
        and (blocked_objects is None or get_object_tag(tool_config) not in blocked_objects)
        and (required_arguments is None or required_arguments.issubset(tool_config.arguments.keys()))
    }

