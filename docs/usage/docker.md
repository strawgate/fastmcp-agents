# Using FastMCP Agents in Docker

While using `uv` and `python` is recommended, you can also use FastMCP Agents in Docker.

## Example: Running a Bundled Server with Docker

Here's how you can configure a bundled server like `mcp-server-tree-sitter` to run within a Docker container:

```json
"mcp-server-tree-sitter": {
  "command": "docker",
  "args": [
    "run",
    "-i",
    "--rm",
    "-e", "GEMINI_API_KEY=YOUR_GEMINI_API_KEY",
    "ghcr.io/strawgate/fastmcp-agents",
    "cli",
    "agent",
    "--name","ask_tree_sitter",
    "--description", "Ask the tree-sitter agent to find items in the codebase.",
    "--instructions", "You are a helpful assistant that provides users a simple way to find items in their codebase.",
    "wrap",
    "uvx", "mcp-server-tree-sitter"
  ]
}
```

## Running a Bundled Server via the CLI in Docker

You can also directly run a bundled server using the FastMCP Agents CLI within a Docker container:

```bash
docker run -i --rm -e GEMINI_API_KEY=YOUR_GEMINI_API_KEY ghcr.io/strawgate/fastmcp-agents cli config --bundled motherduckdb_mcp-server-motherduck run
```