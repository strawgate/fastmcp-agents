A version of [Claude Code](https://github.com/anthropics/claude-code) that is wrapped with an agent and has improved descriptions and parameter names for the Git tools.

| Agent Name | Agent Description |
|------------|-------------------|
| `ask_claude_code_agent` | Assists with running Claude Code. |

# Usage
1. [Run with MCP Inspector](#run-with-mcp-inspector)
2. [Directly call tools via the CLI](#directly-call-tools-via-the-cli)
3. [Use in an MCP Server configuration](#use-in-an-mcp-server-configuration)
4. [Use in Open WebUI](#use-in-open-webui)

# Using Claude Code with Anthropic

See https://docs.anthropic.com/en/docs/claude-code/cli-usage

# Using Claude Code with Vertex AI

Using Claude Code with Vertex AI requires setting the following environment variables:

```bash
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION=us-east5
export ANTHROPIC_VERTEX_PROJECT_ID=YOUR-PROJECT-ID
```

## Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled claude_claude-code-mcp run`

When you setup the Inspector for the first time the timeout will default to 10s. Ensure you modify this to 120s or more under "Configuration" > "Request Timeout" in MCP Inspector.

## Directly call tools via the CLI

```
uvx fastmcp_agents config --bundled claude_claude-code-mcp \
call ask_claude_code_agent '{"task": "Clone the https://github.com/modelcontextprotocol/servers.git repository for me."}' \
run
```

## Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "augmented_claude-code": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "claude_claude-code-mcp",
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
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled claude_claude-code-mcp run
```