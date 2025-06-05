"""Logging configuration for FastMCP Agents."""

import logging
from typing import Literal

from fastmcp.utilities.logging import get_logger
from rich.console import Console
from rich.logging import RichHandler

BASE_LOGGER = get_logger("agents")


def setup_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "INFO",
):
    handler = RichHandler(
        console=Console(stderr=True),
        rich_tracebacks=False,
    )
    formatter = logging.Formatter("%(name)s : %(message)s")
    handler.setFormatter(formatter)

    BASE_LOGGER.setLevel(level)
    BASE_LOGGER.addHandler(handler)
    BASE_LOGGER.propagate = False

    logging.getLogger("mcp").setLevel("WARNING")


def get_logger(name: str) -> logging.Logger:
    """Get a logger nested under FastMCP namespace.

    Args:
        name: the name of the logger, which will be prefixed with 'FastMCP.'

    Returns:
        a configured logger instance
    """
    return BASE_LOGGER.getChild(name)
