To run an augmented server without cloning the repository, you can use the following command:

```bash
export MODEL="vertex_ai/gemini-2.5-flash-preview-05-20"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/credentials.json"

uvx --from git+https://github.com/strawgate/fastmcp-agents fastmcp_agents --config-file "https://github.com/strawgate/fastmcp-agents/blob/main/augmented/servers/github_mcp-server.yml"
```

To expose over SSE, add `--mcp-transport sse`