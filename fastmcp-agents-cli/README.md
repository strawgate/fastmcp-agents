This is a CLI for the FastMCP Agents project. The CLI serves two goals:
1. It is a tool for running tool calls against a FastMCP Agents Server using the command line.
2. It is a tool for loading simple FastMCP Agents from a yaml file and running them.

# Installation

```bash
uvx fastmcp-agents-cli
```

## Quick Start

### Running a FastMCP Agents Server

```bash
fastmcp-agents-cli server
```

### Running a FastMCP Agents Client

By default, the CLI will load the `mcp.json` file in the current directory.

```bash
fastmcp-agents-cli client call <tool-name> <tool-arguments>
```

Tool arguments can be provided as key-value pairs. Everything after the tool name is passed as an argument to the tool:

```bash
fastmcp-agents-cli client call fetch --url https://example.com
```

So if you want to customize the output format or other options they must go before the tool name:

```bash
fastmcp-agents-cli client call --format yaml fetch --url https://example.com
```

You can also pass arguments as a JSON string:

```bash
fastmcp-agents-cli client call fetch --json '{"url": "https://example.com"}'
```

JSON arguments will override other arguments.


Use `--mcp.config` to specify a custom MCP configuration file path.