A version of the [DuckDuckGo MCP server](https://github.com/nickclyde/duckduckgo-mcp-server) that is wrapped with an agent and has improved descriptions and parameter names for the DuckDuckGo tools.

| Agent Name | Agent Description |
|------------|-------------------|
| `duckduckgo_agent` | Ask the duckduckgo agent to perform web searches on your behalf. |

# Usage
1. [Run with MCP Inspector](#run-with-mcp-inspector)
2. [Directly call tools via the CLI](#directly-call-tools-via-the-cli)
3. [Use in an MCP Server configuration](#use-in-an-mcp-server-configuration)
4. [Use in Open WebUI](#use-in-open-webui)

## Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled nickclyde_duckduckgo-mcp-server run`

When you setup the Inspector for the first time the timeout will default to 10s. Ensure you modify this to 120s or more under "Configuration" > "Request Timeout" in MCP Inspector.

## Directly call tools via the CLI

```bash
uv run fastmcp_agents config --bundled nickclyde_duckduckgo-mcp-server \
    call duckduckgo-agent '{"task": "Search for recipes for preparing fried cheese curds."}' \
    run
```

Now run the same server with modified instructions and a change to the agent as tool:

```bash
uv run fastmcp_agents cli \
    agent \
    --name ddg-agent \
    --description "Search with DuckDuckGo" \
    --instructions "You are an assistant who refuses to show results from allrecipes.com.  " \
    call ddg-agent '{"task": "Search for recipes for preparing fried cheese curds."}' \
    wrap uv run fastmcp_agents config --bundled nickclyde_duckduckgo-mcp-server run
```

Close inspection will show that the search query changes from:

```
{'query': 'fried cheese curds recipes'}
```

to:

```
{'query': 'recipes for preparing fried cheese curds -site:allrecipes.com'}
```

## Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "augmented_duckduckgo": {
            "command": "uv",
            "args": [
                "run",
                "fastmcp_agents",
                "config", "--bundled", "nickclyde_duckduckgo-mcp-server",
                "run"
            ]
        }
    }
}
```