# Command Line Interface (CLI) Guide

The FastMCP-Agents CLI allows you to wrap existing MCP servers, define agents, and interact with them directly from your terminal. It provides a flexible way to configure and run your augmented servers.

## Basic Usage and Global Options

The main entry point for the CLI is `uvx fastmcp_agents`. You can use global options before specifying a command group or command.

```bash
uvx fastmcp_agents [GLOBAL_OPTIONS] [COMMAND_GROUP] [COMMAND] [COMMAND_OPTIONS] [ARGUMENTS]
```

**Global Options:**

*   `--transport [stdio|sse|streamable-http]`: The transport to use for the MCP server. (default: `stdio`)
*   `--log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]`: The logging level to use for the agent. (default: `INFO`)
*   `--agent-only`: Only run the agents, don't expose the tools to the client. (flag)
*   `--tool-only`: Only run the tools, don't expose the agents to the client. (flag)

## Command Groups

The CLI is organized into command groups: `cli` and `config`.

### `cli` Command Group

The `cli` command group allows you to build agents and wrap servers directly from the command line. Commands within this group can be chained.

```bash
uvx fastmcp_agents cli [COMMAND] [OPTIONS] [ARGUMENTS]
```

**Commands:**

*   `agent`: Build an agent over the command line.
    *   `--name TEXT`: The name of the agent to wrap. (Required)
    *   `--description TEXT`: The description of the agent to wrap. (Required)
    *   `--instructions TEXT`: The instructions of the agent to wrap. (Required)
    *   `--allowed-tools TEXT`: A comma separated list of the tools that the agent can use.
    *   `--blocked-tools TEXT`: A comma separated list of the tools that the agent cannot use.
*   `list`: List the tools available on the server.
*   `call NAME PARAMETERS`: Add a tool call to the pending tool calls list.
    *   `NAME`: The name of the tool to call.
    *   `PARAMETERS`: A JSON string of the arguments for the tool call.
*   `wrap DIRECT_WRAP_ARGS...`: Take the last of the cli args and use them to run the mcp server and run it.
    *   `--env TEXT`: Environment variables to set for the server (can be used multiple times).
    *   `DIRECT_WRAP_ARGS...`: The command and arguments to run the MCP server.

**Examples:**

**Wrapping an MCP Server with a single agent:**

```bash
uvx fastmcp_agents cli \
agent \
--name "ask_tree_sitter" \
--description "Ask the tree-sitter agent to find items in the codebase." \
--instructions "You are a helpful assistant that provides users a simple way to find items in their codebase." \
wrap uvx git+https://github.com/wrale/mcp-server-tree-sitter.git
```

**Wrapping an MCP Server with several agents and performing a single tool call:**

```bash
uvx fastmcp_agents cli \
agent \
--name "ask_tree_sitter" \
--description "Ask the tree-sitter agent to find items in the codebase." \
--instructions "You are a helpful assistant that provides users a simple way to find items in their codebase." \
agent \
--name "learn_tree_sitter" \
--description "Learn from the tree-sitter agent while it finds items in the codebase." \
--instructions "You are a helpful assistant that provides users a simple way to find items in their codebase. In addition to helping the user, you will thoroughly explain what tools you used and how you used them to solve the user's problem." \
call learn_tree_sitter '{ "instructions": "Analyze the codebase in . and tell me what you found." }' \
wrap uvx git+https://github.com/wrale/mcp-server-tree-sitter.git
```

### `config` Command Group

The `config` command group allows you to load an augmented server configuration from a file, URL, or bundled configuration. Commands within this group can be chained.

```bash
uvx fastmcp_agents config [OPTIONS] [COMMAND] [OPTIONS] [ARGUMENTS]
```

**Options:**

*   `--file TEXT`: The path to the config file to use.
*   `--url TEXT`: The URL of the config file to use.
*   `--directory PATH`: A directory of config files, from which `--file` is relative to. Can also be set via the `FASTMCP_AGENTS_CONFIG_DIR` environment variable.
*   `--bundled TEXT`: The name of the bundled server configuration to use.

**Commands:**

*   `run`: Run the server based on the loaded configuration.
*   `list`: List the tools available on the server loaded from the configuration.
*   `call NAME PARAMETERS`: Add a tool call to the pending tool calls list for the server loaded from the configuration.
    *   `NAME`: The name of the tool to call.
    *   `PARAMETERS`: A JSON string of the arguments for the tool call.

**Examples:**

**Invoking FastMCP-Agents with a bundled configuration:**

```bash
uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter run
```

**Invoking a single tool call using a bundled configuration:**

```bash
uvx fastmcp_agents \
config --bundled wrale_mcp-server-tree-sitter \
call ask_tree_sitter '{"instructions": "Analyze the codebase in . and tell me what you found."}' \
run
```

**Invoking FastMCP-Agents with a configuration file:**

```bash
uvx fastmcp_agents config --file path/to/your/config.yml run
```

## Unimplemented Features

*   `shell`: Start a shell session with the server. This feature is currently unimplemented. Contributions are welcome!