"""Functions for loading configurations."""

from pathlib import Path
from urllib.parse import ParseResult, urlparse

import requests
import yaml

from fastmcp_agents.cli.models import (
    AugmentedServerModel,
    OverriddenStdioMCPServer,
)
from fastmcp_agents.observability.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("loader")

BUNDLED_DIR = Path(__file__).parent.parent / "bundled"

SERVER_DIR = Path(__file__).parent.parent / "bundled" / "servers"
FLOW_DIR = Path(__file__).parent.parent / "bundled" / "flows"

DEFAULT_ARG_REPLACEMENTS: dict[str, str] = {
    "bundled": str(BUNDLED_DIR),
}


def get_config_from_string(config_string: str) -> AugmentedServerModel:
    """Serialize a config from a string."""
    return AugmentedServerModel.model_validate(yaml.safe_load(config_string))


def get_config_from_url(config_url: str) -> AugmentedServerModel:
    """Serialize a config from a URL."""
    url: ParseResult = urlparse(config_url)

    config_raw = requests.get(url.geturl(), timeout=10).text
    config = get_config_from_string(config_raw)

    # If there is a file name in the url, remove it and use that as the relative path
    url_path_without_file = url.path.rsplit("/", 1)[0]

    replacements = {
        **DEFAULT_ARG_REPLACEMENTS,
        # Remove the path off the url
        "relative_to_this": url_path_without_file,
    }

    return process_arg_replacements(config, replacements)


def get_config_from_file(file: str, directory: str | None = None) -> AugmentedServerModel:
    """Serialize a config from a file."""

    file_path: Path = (Path(directory) / file) if directory else Path(file)

    if not file_path.exists():
        msg = f"Config file {file_path} not found"
        raise FileNotFoundError(msg)
    config_raw = file_path.read_text(encoding="utf-8")

    config = get_config_from_string(config_raw)

    replacements = {
        **DEFAULT_ARG_REPLACEMENTS,
        "relative_to_this": str(file_path.relative_to(Path(file_path).parent)),
    }

    return process_arg_replacements(config, replacements)


def get_server_dir(server_name: str) -> Path:
    """Get the directory for a bundled server."""
    server_dir = BUNDLED_DIR / server_name
    if not server_dir.exists():
        msg = f"Server directory {server_dir} not found"
        raise FileNotFoundError(msg)
    return server_dir


def get_server_readme(server_name: str) -> str | None:
    """Get the README content for a bundled server."""
    server_dir = get_server_dir(server_name)
    readme_path = server_dir / "README.md"
    if readme_path.exists():
        return readme_path.read_text(encoding="utf-8")
    return None


def get_server_or_flow_dir(server_or_flow_name: str) -> Path:
    """Get the directory for a bundled server or flow."""
    server_or_flow_dir = SERVER_DIR / server_or_flow_name
    if not server_or_flow_dir.exists():
        msg = f"Server or flow directory {server_or_flow_dir} not found"
        raise FileNotFoundError(msg)
    return server_or_flow_dir


def get_config_for_bundled(config_bundled: str) -> AugmentedServerModel:
    """Serialize a config for a bundled server."""
    server_dir = get_server_or_flow_dir(config_bundled)
    server_yml = server_dir / "server.yml"

    if server_yml.exists():
        config_raw = server_yml.read_text(encoding="utf-8")
        config = get_config_from_string(config_raw)
        return process_arg_replacements(config, DEFAULT_ARG_REPLACEMENTS)

    msg = f"Server config file {server_yml} not found"
    raise FileNotFoundError(msg)


def process_arg_replacements(augmented_server_model: AugmentedServerModel, replacements: dict[str, str]) -> AugmentedServerModel:
    """Process arg replacements in a config string."""

    if replacements:
        stdio_servers = [server for server in augmented_server_model.mcpServers.values() if isinstance(server, OverriddenStdioMCPServer)]
        for server in stdio_servers:
            args: list[str] = server.args
            args = [arg.format(**replacements) if isinstance(arg, str) else arg for arg in args]
            server.args = args

    return augmented_server_model
