# MCP Inspector

1. Run `npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter run`
2. Visit http://localhost:6274/#tools
3. Click `Connect` to connect to your MCP Server
4. Click `List Tools`
5. Click `ask_tree_sitter`
6. Interact with the tool via the instructions text area

When you setup the Inspector for the first time the timeout will default to 10s. Ensure you modify this to 120s or more under "Configuration" > "Request Timeout" in MCP Inspector.