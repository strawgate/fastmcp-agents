A version of the [Cyanheads Git MCP server](https://github.com/cyanheads/git-mcp-server) that is wrapped with an agent and has improved descriptions and parameter names for the Git tools.

| Agent Name | Agent Description |
|------------|-------------------|
| `ask_git_agent` | Assists with performing Git operations as requested by the user. |

# Usage
1. [Run with MCP Inspector](#run-with-mcp-inspector)
2. [Directly call tools via the CLI](#directly-call-tools-via-the-cli)
3. [Use in an MCP Server configuration](#use-in-an-mcp-server-configuration)
4. [Use in Open WebUI](#use-in-open-webui)

## Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled cyanheads_git-mcp-server run`

When you setup the Inspector for the first time the timeout will default to 10s. Ensure you modify this to 120s or more under "Configuration" > "Request Timeout" in MCP Inspector.

## Directly call tools via the CLI

```
uvx fastmcp_agents config --bundled cyanheads_git-mcp-server \
call ask_git_agent '{"task": "Clone the https://github.com/modelcontextprotocol/servers.git repository for me."}' \
run
```

## Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "augmented_git": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "cyanheads_git-mcp-server",
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
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled cyanheads_git-mcp-server run
```