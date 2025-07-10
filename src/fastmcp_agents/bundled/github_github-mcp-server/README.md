A version of the [Github MCP server](https://github.com/github/github-mcp-server) that is wrapped with an agent and has improved descriptions and parameter names for the Github tools.

| Agent Name | Agent Description |
|------------|-------------------|
| `ask_github_agent` | Assists with performing GitHub operations as requested by the user. |
| `summarize_github_issue` | Assists with summarizing a GitHub issue and comments. |
| `summarize_pull_request` | Request a report on a GitHub pull request. |

# Usage
1. [Run with MCP Inspector](#run-with-mcp-inspector)
2. [Directly call tools via the CLI](#directly-call-tools-via-the-cli)
3. [Use in an MCP Server configuration](#use-in-an-mcp-server-configuration)
4. [Use in Open WebUI](#use-in-open-webui)

## Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled github_github-mcp-server run`

When you setup the Inspector for the first time the timeout will default to 10s. Ensure you modify this to 120s or more under "Configuration" > "Request Timeout" in MCP Inspector.

## Directly call tools via the CLI

```bash
uvx fastmcp_agents config --bundled github_github-mcp-server \
call ask_github_agent '{"task": "Summarize issue #1 in the repository modelcontextprotocol/servers. Include any relevant comments and provide a clear overview of the issue's status and content."}' \
run
```

## Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "augmented_github": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "github_github-mcp-server",
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
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled github_github-mcp-server run
``` 