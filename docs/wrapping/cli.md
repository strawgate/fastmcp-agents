The command line is the simplest way to wrap an MCP Server. It provides limited capabilities, but it's a great way to quickly get started.

## Wrapping an MCP Server with a single agent
```bash
uvx fastmcp_agents cli \
agent \
--name "ask_tree_sitter" \
--description "Ask the tree-sitter agent to find items in the codebase." \
--instructions "You are a helpful assistant that provides users a simple way to find items in their codebase." \
wrap uvx git+https://github.com/wrale/mcp-server-tree-sitter.git
```

## Wrapping an MCP Server with several agents and performing a single tool call
```bash
uvx fastmcp_agents cli \
agent \
--name "ask_tree_sitter" \
--description "Ask the tree-sitter agent to find items in the codebase." \
--instructions "You are a helpful assistant that provides users a simple way to find items in their codebase." \
agent \
--name "learn_tree_sitter" \
--description "Learn from the tree-sitter agent while it finds items in the codebase." \
--instructions "You are a helpful assistant that provides users a simple way to find items in their codebase. In addition to helping the user, you will thoroughly explain what tools you used and how you used them to solve the user's problem." \
call learn_tree_sitter '{ "instructions": "Analyze the codebase in . and tell me what you found." }' \
wrap uvx git+https://github.com/wrale/mcp-server-tree-sitter.git
```