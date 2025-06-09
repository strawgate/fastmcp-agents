# IDEs

Follow the instructions for your IDE to set up the MCP Server.

## Example: Configuring a Tree-Sitter MCP Server in your IDE

Here's an example of how you might configure a `mcp-server-tree-sitter` within your IDE's settings (e.g., in a `.vscode/settings.json` file for VS Code):

```json
"mcp-server-tree-sitter": {
  "command": "uvx",
  "args": [
    "fastmcp_agents", "cli",
    "agent",
    "--name","ask_tree_sitter",
    "--description", "Ask the tree-sitter agent to find items in the codebase.",
    "--instructions", "You are a helpful assistant that provides users a simple way to find items in their codebase.",
    "wrap",
    "uvx", "mcp-server-tree-sitter"
  ]
}
```

This configuration defines an MCP server named `mcp-server-tree-sitter` that runs the `ask_tree_sitter` agent. The agent is configured with a name, description, and instructions, and it wraps the `mcp-server-tree-sitter` using `uvx`.