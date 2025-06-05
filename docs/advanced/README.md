# Advanced Documentation

There's more than just adding an AI Agent in FastMCP-Agents.  You can also modify the tools and parameters of the server to make it easier for the Agent to use.

| Option | Agents | Servers | Override Tools | Wrap Tools |
|--------|--------|---------|----------------|------------|
| [Python](./code_agents/README.md) | ∞ | ∞ | Yes | Yes | 
| [YAML or JSON](./yaml_agents/README.md) | ∞ | ∞ | Yes | No | 
| [Command-line](./cli_only_agents/README.md) | ∞ | 1 | No | No |

To learn more about tool rewriting, see the [Tool Rewriting](./tool_rewriting/README.md) documentation.

## Server Options

```bash
uvx fastmcp_agents [GLOBAL_OPTIONS] [COMMAND_GROUP] [COMMAND] [COMMAND_OPTIONS] [ARGUMENTS]
```

### Global Options

The following global options are available for all commands:

* `--transport [stdio|sse|streamable-http]`: The transport to use for the MCP server.
  * `stdio`: Standard input/output transport (default)
  * `sse`: Server-Sent Events transport
  * `streamable-http`: HTTP streaming transport
* `--log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]`: The logging level to use for the agent. (default: `INFO`)
* `--agent-only`: Only run the agents, don't expose the tools to the client. (flag)
* `--tool-only`: Only run the tools, don't expose the agents to the client. (flag)

### Command Groups, Commands, Options, and Arguments

The CLI is organized into two main command groups:

| Command Group | Docs | Description |
|---------------|------|-------------|
| `cli` | [🔗 Link](./cli_only_agents/README.md) | For building agents and wrapping servers directly from the command line |
| `config` | [🔗 Link](./yaml_agents/README.md) | Load a bundled or custom configuration from file, URL, or bundled server |
