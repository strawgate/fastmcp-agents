import logging

from fastmcp_agents.core.observability.logging import BASE_LOGGER, setup_logging

BASE_LOGGER.setLevel(logging.DEBUG)
setup_logging(level=logging.DEBUG)
