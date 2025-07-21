from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from fastmcp_agents.core.agents.task import TaskAgent


class TaskAgentConfig(TaskAgent):
    """A Configuration model for a TaskAgent."""


DEFAULT_YAML_PATH = Path("mcp.yaml")
DEFAULT_YML_PATH = Path("mcp.yml")
DEFAULT_JSON_PATH = Path("mcp.json")


class CliConfigSource(BaseModel):
    """Context for the MCP client."""

    path: Path | None = Field(default=None, description="The MCP configuration file.")

    module: str | None = Field(default=None, description="The Python module to use for the MCP configuration file.")

    expand_vars: bool = Field(default=False, description="Whether to expand environment variables in the MCP configuration file.")

    def try_default_path(self) -> Path:
        """Try to find the default path."""

        if self.path is not None:
            return self.path

        return next(p for p in [DEFAULT_YAML_PATH, DEFAULT_YML_PATH, DEFAULT_JSON_PATH] if p.exists())


class CliLogOptions(BaseModel):
    """Context for the log settings."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", description="The log level to use for the CLI.")


class CliTagsOptions(BaseModel):
    """Context for the tags."""

    include: set[str] | None = Field(default=None, description="The tags to include in the server.")
    exclude: set[str] | None = Field(default=None, description="The tags to exclude from the server.")
