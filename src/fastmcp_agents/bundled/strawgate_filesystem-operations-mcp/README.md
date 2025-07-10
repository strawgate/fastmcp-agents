A version of the [Filesystem Operations MCP server](https://github.com/strawgate/py-mcp-collection) that is wrapped with an agent..

| Agent Name | Agent Description |
|------------|-------------------|
| `ask_filesystem_operations_agent` | Ask the Filesystem Operations agent to perform filesystem operations on your behalf. |

# Usage
1. [Run with MCP Inspector](#run-with-mcp-inspector)
2. [Directly call tools via the CLI](#directly-call-tools-via-the-cli)
3. [Use in an MCP Server configuration](#use-in-an-mcp-server-configuration)
4. [Use in Open WebUI](#use-in-open-webui)

## Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled strawgate_filesystem-operations-mcp run`

When you setup the Inspector for the first time the timeout will default to 10s. Ensure you modify this to 120s or more under "Configuration" > "Request Timeout" in MCP Inspector.

## Directly call tools via the CLI

```bash
uvx fastmcp_agents config --bundled strawgate_filesystem-operations-mcp \
call ask_filesystem_operations_agent '{"task": "Create a new file called 'test.txt' in the current directory."}' \
run
```

## Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "augmented_filesystem": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "strawgate_filesystem-operations-mcp",
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
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled strawgate_filesystem-operations-mcp run
``` 