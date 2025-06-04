from importlib.metadata import version

from fastmcp_agents.agent.fastmcp import FastMCPAgent

__version__ = version("fastmcp_agents")

__all__ = ["FastMCPAgent"]
