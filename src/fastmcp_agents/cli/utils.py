from __future__ import annotations

import logging
import os
from pathlib import Path

import requests
import yaml
from fastmcp import Client, FastMCP

from fastmcp_agents.cli.models import (
    AgentConfig,
    ContentTools,
    FastMCPAgentsConfig,
    MCPConfigWithOverrides,
    RemoteMCPServerWithOverrides,
    StdioMCPServerWithOverrides,
    load_agents,
)
from fastmcp_agents.observability.logging import BASE_LOGGER
from fastmcp_agents.vendored.tool_transformer.loader import proxy_mcp_server_with_overrides

logger = BASE_LOGGER.getChild("main")

ROOT_LOGGER = logging.getLogger()

ROOT_LOGGER.setLevel(logging.WARNING)

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None:
    from fastmcp_agents.observability.otel import setup_otel

    setup_otel()

MCP_TRANSPORT_HELP = """
The transport to use for the MCP server.

- stdio: Use the standard input and output streams.
- sse: Use Server-Sent Events.
- streamable-http: Use the Streamable HTTP transport.
"""


def split_config(config: FastMCPAgentsConfig) -> tuple[MCPConfigWithOverrides, ContentTools, list[AgentConfig]]:
    mcp_config_with_overrides = MCPConfigWithOverrides(mcpServers=config.mcpServers)
    content_tools = ContentTools(tools=config.tools)
    return mcp_config_with_overrides, content_tools, config.agents


def get_config_from_url(config_url: str) -> tuple[MCPConfigWithOverrides, ContentTools, list[AgentConfig]]:
    config_raw = requests.get(config_url, timeout=10).text
    config = FastMCPAgentsConfig.model_validate(yaml.safe_load(config_raw))
    return split_config(config)


def get_config_from_file(config_file: str) -> tuple[MCPConfigWithOverrides, ContentTools, list[AgentConfig]]:
    if not Path(config_file).exists():
        msg = f"Config file {config_file} not found"
        raise FileNotFoundError(msg)
    config_raw = Path(config_file).read_text(encoding="utf-8")
    config = FastMCPAgentsConfig.model_validate(yaml.safe_load(config_raw))
    return split_config(config)


def get_config_from_bundled(config_bundled: str) -> tuple[MCPConfigWithOverrides, ContentTools, list[AgentConfig]]:
    bundled_dir = Path(__file__).parent.parent / "bundled" / "servers"
    bundled_server_settings_path: Path = bundled_dir / f"{config_bundled}.yml"

    if not bundled_server_settings_path.exists():
        msg = f"Bundled server config file {bundled_server_settings_path} not found"
        raise FileNotFoundError(msg)

    config_raw = bundled_server_settings_path.read_text(encoding="utf-8")

    config = FastMCPAgentsConfig.model_validate(yaml.safe_load(config_raw))
    return split_config(config)


async def prepare_mcp_servers(
    tool_server: FastMCP, mcp_servers_with_overrides: dict[str, StdioMCPServerWithOverrides | RemoteMCPServerWithOverrides]
) -> tuple[dict[str, Client], dict[str, FastMCP]]:
    """Prepare the MCP servers with Tool overrides.

    Args:
        tool_server: The server to mount the tools into.
        mcp_servers_with_overrides: The MCP servers with overrides.

    Returns:
        The MCP servers.
    """
    mcp_servers: dict[str, FastMCP] = {}
    mcp_clients: dict[str, Client] = {}

    for mcp_server_name, mcp_server_settings in mcp_servers_with_overrides.items():
        logger.info("Preparing MCP server %s", mcp_server_name)
        overrides = mcp_server_settings.get_tool_overrides()

        mcp_client, mcp_server = await proxy_mcp_server_with_overrides(
            mcp_server_name, mcp_server_settings, tool_overrides=overrides, target_server=tool_server
        )

        mcp_clients[mcp_server_name] = mcp_client
        mcp_servers[mcp_server_name] = mcp_server

        mcp_server_tools = await mcp_server.get_tools()
        logger.info(f"MCP server {mcp_server_name} offers {len(mcp_server_tools)} tools: {mcp_server_tools} ({len(overrides)} overriden).")

    return mcp_clients, mcp_servers


async def prepare_server(
    server_name: str,
    mcp_config_with_overrides: MCPConfigWithOverrides,
    agents_config: list[AgentConfig],
    content_tools: ContentTools,
    agent_only: bool,
    tool_only: bool,
) -> tuple[dict[str, Client], dict[str, FastMCP], FastMCP]:
    """Prepare the server for the agents and tools.

    Args:
        server_name: The name of the server.
        agents_config: The agents config.
        agent_only: Whether to only expose the agents.
        tool_only: Whether to only expose the tools.
    """

    tools_server = FastMCP(name=server_name)

    mcp_clients, mcp_servers = await prepare_mcp_servers(tools_server, mcp_config_with_overrides.mcpServers)

    tools_server_tools = await tools_server.get_tools()
    tools_server_tools_names = [tool.name for tool in tools_server_tools.values()]

    for tool_name, tool_config in content_tools.tools.items():

        def content_tool_factory(content: str):
            def content_tool() -> str:
                return content

            return content_tool

        tools_server.add_tool(fn=content_tool_factory(tool_config.returns), name=tool_name, description=tool_config.description)

    if tool_only:
        logger.info(f"Tool-only server with {len(tools_server_tools)} tools: {tools_server_tools_names}.")
        return mcp_clients, mcp_servers, tools_server

    agents_server = tools_server

    if agent_only:
        agents_server = FastMCP(name="agents")

    agents = load_agents(agents_config, tools=list(tools_server_tools.values()))
    agent_names = [agent.name for agent in agents]

    for agent in agents:
        agents_server.add_tool(fn=agent.currate, name=agent.name, description=agent.description)

    if agent_only:
        logger.info(f"Agent-only server with {len(agents)} agents: {agent_names}.")
    else:
        logger.info(f"Server with{len(agents)} agents: {agent_names} and {len(tools_server_tools)} tools: {tools_server_tools_names}.")

    return mcp_clients, mcp_servers, agents_server


# async def transfer_tools_to_server(
#     server_name: str, server_settings: StdioMCPServerWithOverrides | RemoteMCPServerWithOverrides, frontend_server: FastMCP
# ):
#     logger.info("Transforming tools from %s to frontend server", server_name)

#     if isinstance(server_settings, StdioMCPServerWithOverrides) and isinstance(server_settings.env, dict):
#         # if "ALL" in server_settings.env:
#         server_settings.env = dict(os.environ.items())

#         # # limit to specific environment variables
#         # for env_name, env_value in os.environ.items():
#         #     if env_name not in server_settings.env:
#         #         server_settings.env[env_name] = env_value

#     # mcp_client = Client(MCPConfig(mcpServers={server_name: server_settings}), timeout=30.0)
#     extra_tools_and_overrides = ExtraToolsAndOverrides(tools=server_settings.tools)

#     extra_tools: ContentTools = extra_tools_and_overrides.get_content_tools()
#     tool_overrides: ToolOverrides = extra_tools_and_overrides.get_tool_overrides()

#     connection = MCPServerConnection(server_name, server_settings)
#     await connection.connect()
#     server = FastMCP.as_proxy(connection._client)

#     backend_tools = await server.get_tools()
#     logger.debug(f"Backend server: {server}, overrides: {tool_overrides}, tools: {backend_tools}")

#     await transform_tool(server, frontend_server, overrides=tool_overrides)

#     for tool_name, tool_config in extra_tools.tools.items():

#         def content_tool_factory(content: str):
#             def content_tool() -> str:
#                 return content

#             return content_tool

#         frontend_server.add_tool(fn=content_tool_factory(tool_config.returns), name=tool_name, description=tool_config.description)


# @click.option("--agent-name", help="The name of the agent to wrap.", multiple=True)
# @click.option("--agent-description", help="The description of the agent to wrap.", multiple=True)
# @click.option("--agent-instructions", help="The instructions of the agent to wrap.", multiple=True)
# @click.option("--agent-allowed-tools", help="A comma separated list of the tools that the agent can use.", multiple=True)
# @click.option("--agent-blocked-tools", help="A comma separated list of the tools that the agent cannot use.", multiple=True)
# @click.pass_context
# def cli(
#     ctx: click.Context,
#     agent_name: list[str],
#     agent_description: list[str],
#     agent_instructions: list[str],
#     agent_allowed_tools: list[str],
#     agent_blocked_tools: list[str],
#     direct_wrap_args: list[str],
#     **kwargs: Any,
# ) -> Any:
#     agent_configs: list[AgentConfig] = []

#     for i, this_agent_name in enumerate(agent_name):
#         this_agent_description = agent_description[i]
#         this_agent_instructions = agent_instructions[i]
#         this_agent_allowed_tools = agent_allowed_tools[i].split(",") if agent_allowed_tools[i] else None
#         this_agent_blocked_tools = agent_blocked_tools[i].split(",") if agent_blocked_tools[i] else None

#         agent_configs.append(
#             AgentConfig(
#                 name=this_agent_name,
#                 description=this_agent_description,
#                 default_instructions=this_agent_instructions,
#                 allowed_tools=this_agent_allowed_tools,
#                 blocked_tools=this_agent_blocked_tools,
#             )
#         )

#     ctx.obj.agent_configs = agent_configs

#     if len(direct_wrap_args) == 0:
#         raise NoServerToWrapError

#     command = direct_wrap_args[0]
#     args = direct_wrap_args[1:] if len(direct_wrap_args) > 1 else []
#     env = os.environ.copy()

#     mcp_config = MCPConfigWithOverrides(
#         mcpServers={
#             "main": StdioMCPServerWithOverrides(
#                 command=command,
#                 args=args,
#                 env=env,
#             )
#         }
#     )

#     ctx.obj.mcp_config_with_overrides = mcp_config


# def config_file_options(f: Callable[..., Any]) -> Callable[..., Any]:
#     """Config file options."""

#     @click.option("--config-file", type=click.Path(exists=True), help="The config file to use.")
#     @click.option("--config-url", type=str, help="The URL of the config file to use.")
#     @click.option("--config-bundled", type=str, help="The bundled server to use.")
#     @click.pass_context
#     @functools.wraps(f)
#     def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
#         config_file = kwargs.pop("config_file")
#         config_url = kwargs.pop("config_url")
#         config_bundled = kwargs.pop("config_bundled")

#         if config_file:
#             mcp_config_with_overrides, agents_config = get_config_from_file(config_file)
#         elif config_url:
#             mcp_config_with_overrides, agents_config = get_config_from_url(config_url)
#         elif config_bundled:
#             mcp_config_with_overrides, agents_config = get_config_from_bundled(config_bundled)
#         else:
#             raise NoConfigError

#         ctx.obj.mcp_config_with_overrides = mcp_config_with_overrides
#         ctx.obj.agents_config = agents_config

#         return f(*args, **kwargs)

#     return wrapper


# class CliContext(BaseModel):
#     server_settings: ServerSettings
#     agents_config: list[AgentConfig] | None = None
#     mcp_config_with_overrides: MCPConfigWithOverrides | None = None


# @click.group()
# @click.option("--transport", type=click.Choice(["stdio", "sse", "streamable-http"]), default="stdio", help=MCP_TRANSPORT_HELP)
# @click.option(
#     "--log-level",
#     type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
#     default="INFO",
#     help="The logging level to use for the agent.",
# )
# @click.option("--agent-only", is_flag=True, help="Only run the agents, don't expose the tools to the client.")
# @click.option("--tool-only", is_flag=True, help="Only run the tools, don't expose the agents to the client.")
# @click.option("--config-file", type=click.Path(exists=True), help="The config file to use.")
# @click.option("--config-url", type=str, help="The URL of the config file to use.")
# @click.option("--config-bundled", type=str, help="The bundled server to use.")
# @click.pass_context
# async def cli(
#     ctx: click.Context,
#     transport: Literal["stdio", "sse", "streamable-http"],
#     log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
#     agent_only: bool = False,
#     tool_only: bool = False,
#     config_file: str | None = None,
#     config_url: str | None = None,
#     config_bundled: str | None = None,
# ):
#     agents_config: list[AgentConfig] | None = None
#     mcp_config_with_overrides: MCPConfigWithOverrides | None = None

#     # if more than one of the config options is provided, raise an error
#     if len([x for x in [config_file, config_url, config_bundled] if x is not None]) > 1:
#         raise MultipleConfigOptionsError

#     if config_url:
#         mcp_config_with_overrides, agents_config = get_config_from_url(config_url)
#     elif config_file:
#         mcp_config_with_overrides, agents_config = get_config_from_file(config_file)
#     elif config_bundled:
#         mcp_config_with_overrides, agents_config = get_config_from_bundled(config_bundled)

#     # Configure FastMCP Logging
#     configure_logging(level=log_level, logger=BASE_LOGGER.getChild("FastMCP"))

#     # Set the logging level
#     BASE_LOGGER.setLevel(log_level)

#     ctx.obj = CliContext(
#         server_settings=ServerSettings(
#             transport=transport,
#             log_level=log_level,
#             agent_only=agent_only,
#             tool_only=tool_only,
#         ),
#         agents_config=agents_config,
#         mcp_config_with_overrides=mcp_config_with_overrides,
#     )


# @cli.group()
# @click.option("--config-file", type=click.Path(exists=True), help="The config file to use.")
# @click.option("--config-url", type=str, help="The URL of the config file to use.")
# @click.option("--config-bundled", type=str, help="The bundled server to use.")
# @click.pass_context
# async def cli_with_config(
#     ctx: click.Context, config_file: str | None = None, config_url: str | None = None, config_bundled: str | None = None
# ):
#     if config_url:
#         agents_config = get_config_from_url(config_url)
#     elif config_file:
#         agents_config = get_config_from_file(config_file)
#     elif config_bundled:
#         agents_config = get_config_from_bundled(config_bundled)
#     else:
#         raise NoConfigError

#     ctx.obj.agents_config = agents_config


# @cli.group()
# @click.option("--agent-name", help="The name of the agent to wrap.", multiple=True)
# @click.option("--agent-description", help="The description of the agent to wrap.", multiple=True)
# @click.option("--agent-instructions", help="The instructions of the agent to wrap.", multiple=True)
# @click.option("--agent-allowed-tools", help="A comma separated list of the tools that the agent can use.", multiple=True)
# @click.option("--agent-blocked-tools", help="A comma separated list of the tools that the agent cannot use.", multiple=True)
# @click.argument("direct-wrap-args", nargs=-1, type=click.UNPROCESSED)
# @click.pass_context
# async def cli_with_args(
#     ctx: click.Context,
#     agent_name: list[str],
#     agent_description: list[str],
#     agent_instructions: list[str],
#     agent_allowed_tools: list[str],
#     agent_blocked_tools: list[str],
#     direct_wrap_args: list[str],
# ):
#     agent_configs: list[AgentConfig] = []

#     if len(direct_wrap_args) == 0:
#         raise NoServerToWrapError

#     command = direct_wrap_args[0]
#     args = direct_wrap_args[1:] if len(direct_wrap_args) > 1 else []
#     env = os.environ.copy()

#     mcp_config = MCPConfigWithOverrides(
#         mcpServers={
#             "main": StdioMCPServerWithOverrides(
#                 command=command,
#                 args=args,
#                 env=env,
#             )
#         }
#     )

#     ctx.obj.mcp_config_with_overrides = mcp_config

#     if len(agent_name) != len(agent_description) or len(agent_name) != len(agent_instructions):
#         msg = "The number of agent names, descriptions, and instructions must be the same."
#         raise ValueError(msg)

#     for i, agent in enumerate(agent_name):
#         this_agent_name = agent
#         this_agent_description = agent_description[i]
#         this_agent_instructions = agent_instructions[i]
#         this_agent_allowed_tools = agent_allowed_tools[i].split(",") if agent_allowed_tools[i] else None
#         this_agent_blocked_tools = agent_blocked_tools[i].split(",") if agent_blocked_tools[i] else None

#         agent_configs.append(
#             AgentConfig(
#                 name=this_agent_name,
#                 description=this_agent_description,
#                 default_instructions=this_agent_instructions,
#                 allowed_tools=this_agent_allowed_tools,
#                 blocked_tools=this_agent_blocked_tools,
#             )
#         )

#     ctx.obj.agent_configs = agent_configs


# @cli.command(name="run")
# @click.pass_context
# async def run_server(ctx: click.Context):
#     cli_context: CliContext = ctx.obj

#     if cli_context.agents_config is None:
#         raise NoConfigError

#     if cli_context.mcp_config_with_overrides is None:
#         raise NoConfigError

#     server = await prepare_server(
#         "fastmcp_agents",
#         cli_context.mcp_config_with_overrides,
#         cli_context.agents_config,
#         cli_context.server_settings.agent_only,
#         cli_context.server_settings.tool_only,
#     )

#     await server.run_async(transport=cli_context.server_settings.transport)


# # @cli.command(name="agent")
# # @click.argument("agent")
# # @click.argument("instructions")
# # async def invoke_agent(
# #     agent: str,
# #     instructions: str,
# #     config_file: str,
# #     config_url: str,
# #     agent_only: bool,
# #     tool_only: bool,
# #     prompt_suggestions_dir: Path | None = None,
# # ):
# #     config = get_config_from_url(config_url) if config_url else get_config_from_file(config_file)

# #     server = await prepare_server(config, agent_only, tool_only)

# #     client = Client(server)

# #     async with client as agent_client:
# #         return await agent_client.call_tool(name=agent, arguments={"instructions": instructions})


# # @cli.command(name="bundled")
# # @click.argument("bundled-source")
# # @click.argument("bundled-server")
# # @prompt_suggestions_dir_option
# # async def bundled_server_cli(
# #     ctx: click.Context,
# #     bundled_source: str,
# #     bundled_server: str,
# # ):
# #     server_settings: ServerConfig = ctx.obj

# #     bundled_dir = Path(__file__).parent / "servers"

# #     bundled_server_settings_path: Path = bundled_dir / f"{bundled_source}_{bundled_server}.yml"

# #     if not bundled_server_settings_path.exists():
# #         msg = f"Bundled server config file {bundled_server_settings_path} not found"
# #         raise FileNotFoundError(msg)

# #     agents_config = get_config_from_file(str(bundled_server_settings_path))

# #     server = await prepare_server(agents_config, server_settings.agent_only, server_settings.tool_only)

# #     await server.run_async(transport=server_settings.transport)


# @cli_with_args.command(
#     name="wrap",
#     context_settings={
#         "ignore_unknown_options": True,
#         "allow_extra_args": True,
#     },
# )
# @click.pass_context
# async def wrap_server(
#     ctx: click.Context,
# ):
#     cli_context: CliContext = ctx.obj

#     if cli_context.mcp_config_with_overrides is None:
#         raise NoConfigError

#     if cli_context.agents_config is None:
#         raise NoConfigError

#     server = await prepare_server(
#         server_name="wrap",
#         mcp_config_with_overrides=cli_context.mcp_config_with_overrides,
#         agents_config=cli_context.agents_config,
#         agent_only=cli_context.server_settings.agent_only,
#         tool_only=cli_context.server_settings.tool_only,
#     )

#     await server.run_async(transport=cli_context.server_settings.transport)


# cli_with_config.add_command(wrap_server)


# def run_mcp():
#     asyncio.run(cli())


# if __name__ == "__main__":
#     run_mcp()
