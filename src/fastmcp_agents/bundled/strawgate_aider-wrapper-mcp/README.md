A version of [Aider](https://github.com/aider-ai/aider) that is wrapped with an agent and has improved descriptions and parameter names for the Git tools.

| Agent Name | Agent Description |
|------------|-------------------|
| `ask_aider_agent` | Assists with running Aider. |

# Usage
1. [Run with MCP Inspector](#run-with-mcp-inspector)
2. [Directly call tools via the CLI](#directly-call-tools-via-the-cli)
3. [Use in an MCP Server configuration](#use-in-an-mcp-server-configuration)
4. [Use in Open WebUI](#use-in-open-webui)

## Using Aider

Aider should inherit the environment variables from the parent process and should use the same model as you have already configured for fastmcp_agents.

Running Aider generally requires having first cloned the repository you want to work on.

## Using Aider with Vertex AI

Using Aider with Vertex AI requires setting the following environment variables:

```bash
export MODEL=vertex_ai/gemini-2.5-flash-preview-05-20
export VERTEXAI_PROJECT=elastic-platform-ingest
export VERTEXAI_LOCATION=us-central1
```

## Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled strawgate_aider-wrapper-mcp run`

When you setup the Inspector for the first time the timeout will default to 10s. Ensure you modify this to 120s or more under "Configuration" > "Request Timeout" in MCP Inspector.

## Directly call tools via the CLI

```
uvx fastmcp_agents config --bundled strawgate_aider-wrapper-mcp \
call ask_aider_agent '{"task": "Write a readme for me."}' \
run
```

## Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "augmented_aider": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "strawgate_aider-wrapper-mcp",
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
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled strawgate_aider-wrapper-mcp run
```