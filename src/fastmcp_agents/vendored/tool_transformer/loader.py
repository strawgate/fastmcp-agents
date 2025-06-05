"""Functions for loading tool transformation configurations."""

import json
from pathlib import Path
from typing import Any

import yaml

from fastmcp_agents.vendored.tool_transformer.models import ToolOverride


def overrides_from_dict(obj: dict[str, Any]) -> dict[str, ToolOverride]:
    return {tool_name: ToolOverride.model_validate(tool_override) for tool_name, tool_override in obj.items()}


def overrides_from_yaml(yaml_str: str) -> dict[str, ToolOverride]:
    return overrides_from_dict(yaml.safe_load(yaml_str))


def overrides_from_yaml_file(yaml_file: Path) -> dict[str, ToolOverride]:
    with Path(yaml_file).open(encoding="utf-8") as f:
        return overrides_from_yaml(yaml_str=f.read())


def overrides_from_json(json_str: str) -> dict[str, ToolOverride]:
    return overrides_from_dict(json.loads(json_str))


def overrides_from_json_file(json_file: Path) -> dict[str, ToolOverride]:
    with Path(json_file).open(encoding="utf-8") as f:
        return overrides_from_json(f.read())
