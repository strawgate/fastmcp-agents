

| Server | Description | Enhancements | Command |
|--------|-------------|---------|---------|
| Git (from MCP) | Embedded Git Agent for Git Operations | Better descriptions and parameter names | ```{"command": "uvx", "args": ["fastmcp_agents","config","--bundled","mcp_git"]}``` |
| Git (from Cyanheads) | Embedded Git Agent for Git Operations | Fix git_clone depth 0 issue | `{"command": "uvx", "args": ["fastmcp_agents","config","--bundled","cyanheads_git-mcp-server"]}` |
| Github | Embedded Github Agent for Issue Triage | Added tool for getting docs on GitHub query syntax | `{"command": "uvx", "args": ["fastmcp_agents","config","--bundled","github_github-mcp-server"]}` |
| Tree Sitter | Embedded Tree Sitter Agent for Code Search | Added tool for getting docs on GitHub query syntax | `{"command": "uvx", "args": ["fastmcp_agents","config","--bundled","wrale_mcp-server-tree-sitter"]}` |
