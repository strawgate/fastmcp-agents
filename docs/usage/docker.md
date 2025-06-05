# Using FastMCP Agents in Docker

While using `uv` and `python` is recommended, you can also use FastMCP Agents in Docker.

```json
"mcp-server-tree-sitter": {
  "command": "docker",
  "args": [
    "run",
    "-i",
    "--rm",
    "-e",
    "cli",
    "ghcr.io/strawgate/fastmcp-agents",
    "agent",
    "--name","ask_tree_sitter",
    "--description", "Ask the tree-sitter agent to find items in the codebase.",
    "--instructions", "You are a helpful assistant that provides users a simple way to find items in their codebase.",
    "wrap", 
    "uvx", "mcp-server-tree-sitter"
  ]
}
```