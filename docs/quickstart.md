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

- [Aider](../src/fastmcp_agents/bundled/servers/strawgate_aider-wrapper-mcp/README.md)
- [Claude Code](../src/fastmcp_agents/bundled/servers/claude_claude-code-mcp/README.md)
- [DuckDB](../src/fastmcp_agents/bundled/servers/motherduckdb_mcp-server-motherduck/README.md)
- [DuckDuckGo (from nickclyde)](../src/fastmcp_agents/bundled/servers/nickclyde_duckduckgo-mcp-server/README.md)
- [Git (from Cyanheads)](../src/fastmcp_agents/bundled/servers/cyanheads_git-mcp-server/README.md)
- [Git (from MCP)](../src/fastmcp_agents/bundled/servers/mcp_git/README.md)
- [Github](../src/fastmcp_agents/bundled/servers/github_github-mcp-server/README.md)
- [Tree Sitter](../src/fastmcp_agents/bundled/servers/wrale_mcp-server-tree-sitter/README.md)

In each doc we include how to run the server with 🔎 MCP Inspector, how to call the tools via the CLI, how to use the server in an MCP Server configuration, and how to use the server in Open WebUI.

## Advanced Topics

- [Advanced Usage](./advanced/README.md) - Advanced usage patterns and configurations
- [Developer Guide](./developer/README.md) - Guide for developers extending FastMCP-Agents 