A version of the [MotherDuckDB MCP server](https://github.com/motherduckdb/mcp-server-motherduck) that is wrapped with an agent and has improved descriptions and parameter names for the MotherDuckDB tools.

| Agent Name | Agent Description |
|------------|-------------------|
| `ask_duckdb_agent` | Ask the duckdb agent to work with an in-memory database on your behalf. |

# Usage
1. [Run with MCP Inspector](#run-with-mcp-inspector)
2. [Directly call tools via the CLI](#directly-call-tools-via-the-cli)
3. [Use in an MCP Server configuration](#use-in-an-mcp-server-configuration)
4. [Use in Open WebUI](#use-in-open-webui)

## Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled motherduckdb_mcp-server-motherduck run`

When you setup the Inspector for the first time the timeout will default to 10s. Ensure you modify this to 120s or more under "Configuration" > "Request Timeout" in MCP Inspector.

## Directly call tools via the CLI

```bash
uvx fastmcp_agents config --bundled motherduckdb_mcp-server-motherduck \
call ask_duckdb_agent '{"task": "Create a table called 'users' with the following columns: id, name, email."}' \
run
```

## Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "augmented_duckdb": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "motherduckdb_mcp-server-motherduck",
                "run"
            ]
        }
    }
}
```

## Use in Open WebUI

Follow the instructions in [Open WebUI](../usage/web_ui.md) to run Open WebUI.

You can expose the server via mcpo:
```bash
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled motherduckdb_mcp-server-motherduck run
``` 