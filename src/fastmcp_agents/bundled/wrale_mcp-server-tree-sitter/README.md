A version of the [Tree Sitter MCP server](https://github.com/wrale/mcp-server-tree-sitter) that is wrapped with an agent and has improved descriptions and parameter names for the Tree Sitter tools.

| Agent Name | Agent Description |
|------------|-------------------|
| `ask_tree_sitter_agent` | Ask the tree-sitter agent to find items in the codebase. It can search for text, symbols, classes, functions, variables, and more. |

# Usage
1. [Run with MCP Inspector](#run-with-mcp-inspector)
2. [Directly call tools via the CLI](#directly-call-tools-via-the-cli)
3. [Use in an MCP Server configuration](#use-in-an-mcp-server-configuration)
4. [Use in Open WebUI](#use-in-open-webui)

## Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter run`

When you setup the Inspector for the first time the timeout will default to 10s. Ensure you modify this to 120s or more under "Configuration" > "Request Timeout" in MCP Inspector.

## Directly call tools via the CLI

```
uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter \
call ask_tree_sitter_agent '{"task": "Tell me all the classes in the repository located in the current working directory."}' \
run
```

## Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "augmented_tree_sitter": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "wrale_mcp-server-tree-sitter",
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
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter run
``` 