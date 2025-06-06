# Setup

FastMCP Agents requires Python 3.10+ and [Installing UV](https://docs.astral.sh/uv/getting-started/installation/) to be installed on your system.

Once you can run `uv --version` you are ready to go.

## Configuring your Provider and Model

| Provider | Setup | Recommended Model |
|----------|-------|-------------------|
| Google Gemini | [Setup](./providers/gemini.md) | `gemini/gemini-2.5-flash-preview-05-20` |
| Google Vertex AI | [Setup](./providers/vertexai.md) | `vertex_ai/gemini-2.5-flash-preview-05-20` |

## Using FastMCP Agents with your preferred client

For more specific instructions on how to use FastMCP Agents with your preferred client, see the following guides:

| MCP Client | Instructions |
|------------|-------|
| Web UI | [Setup](./usage/web_ui.md) |
| Inspector | [Setup](./usage/inspector.md) |
| IDE (VSCode, Roo Code) | [Setup](./usage/ide.md) |
| Docker | [Setup](./usage/docker.md) |

## Start running with the bundled MCP servers

FastMCP-Agents comes bundled with some great MCP Servers. These bundled servers demonstrate how to integrate third-party MCP servers and expose them with augmented agents and tools.

The following bundled servers are available:

- [DuckDuckGo (from nickclyde)](./bundled/servers.md#6-duckduckgo)
- [Git (from Cyanheads)](./bundled/servers.md#1-git-from-cyanheads)
- [Git (from MCP)](./bundled/servers.md#5-git-official-mcp-server)
- [Github](./bundled/servers.md#2-github)
- [MotherDuckDB](./bundled/servers.md#4-motherduckdb)
- [Tree Sitter](./bundled/servers.md#3-tree-sitter)

For the full list, and instructions on how to use the bundled MCP servers, see [Bundled MCP Servers](./bundled/servers.md).

## Advanced Topics

- [Advanced Usage](./advanced/README.md) - Advanced usage patterns and configurations
- [Developer Guide](./developer/README.md) - Guide for developers extending FastMCP-Agents 