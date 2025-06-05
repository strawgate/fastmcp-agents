# IDEs

Follow the instructions for your IDE to setup the MCP Server.

Provide something like the following:
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