from pathlib import Path

import requests
import yaml

from fastmcp_agents.cli.models import (
    AugmentedServerModel,
)
from fastmcp_agents.observability.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("loader")


def get_config_from_string(config_string: str) -> AugmentedServerModel:
    """Serialize a config from a string."""
    return AugmentedServerModel.model_validate(yaml.safe_load(config_string))


def get_config_from_url(config_url: str) -> AugmentedServerModel:
    """Serialize a config from a URL."""
    config_raw = requests.get(config_url, timeout=10).text
    return get_config_from_string(config_raw)


def get_config_from_file(file: str, directory: str | None = None) -> AugmentedServerModel:
    """Serialize a config from a file."""

    file_path: Path = (Path(directory) / file) if directory else Path(file)

    if not file_path.exists():
        msg = f"Config file {file_path} not found"
        raise FileNotFoundError(msg)
    config_raw = file_path.read_text(encoding="utf-8")

    return get_config_from_string(config_raw)


def get_config_for_bundled(config_bundled: str) -> AugmentedServerModel:
    """Serialize a config for a bundled server."""
    bundled_config_path = Path(__file__).parent.parent / "bundled" / "servers" / f"{config_bundled}.yml"

    if not bundled_config_path.exists():
        msg = f"Bundled server config file {bundled_config_path} not found"
        raise FileNotFoundError(msg)

    config_raw = bundled_config_path.read_text(encoding="utf-8")
    return get_config_from_string(config_raw)
