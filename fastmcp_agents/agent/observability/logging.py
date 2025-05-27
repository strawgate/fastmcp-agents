import logging

from rich.console import Console
from rich.logging import RichHandler

BASE_LOGGER = logging.getLogger("fastmcp_agents")

# Only configure the FastMCP logger namespace
handler = RichHandler(
    console=Console(stderr=True),
    rich_tracebacks=True,
)
formatter = logging.Formatter("%(name)s : %(message)s")
handler.setFormatter(formatter)

BASE_LOGGER.setLevel(logging.INFO)
BASE_LOGGER.addHandler(handler)
BASE_LOGGER.propagate = False

