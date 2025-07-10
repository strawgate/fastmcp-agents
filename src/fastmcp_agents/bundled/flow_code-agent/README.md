A Coding Agent that can be used to code in a variety of languages.

| Agent Name | Agent Description |
|------------|-------------------|
| `ask_code_agent` | Ask the Code Agent to perform code operations on your behalf. |

# Usage
1. [Run with MCP Inspector](#run-with-mcp-inspector)
2. [Directly call tools via the CLI](#directly-call-tools-via-the-cli)
3. [Use in an MCP Server configuration](#use-in-an-mcp-server-configuration)
4. [Use in Open WebUI](#use-in-open-webui)

## Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled flow_code-agent run`

When you setup the Inspector for the first time the timeout will default to 10s. Ensure you modify this to 120s or more under "Configuration" > "Request Timeout" in MCP Inspector.

## Directly call tools via the CLI

```bash
uvx fastmcp_agents config --bundled flow_code-agent \
call ask_code_agent '{"task": "Create a new file called 'test.txt' in the current directory."}' \
run
```

## Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "augmented_code": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "flow_code-agent",
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
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled flow_code-agent run
``` 