The YAML or JSON configuration is the second most powerful way to wrap an MCP Server. It allows you to override the tools and parameters of the server, and it's a great way to share your configuration with others.

## Invoking FastMCP-Agents with a YAML or JSON configuration

Simply use `uvx fastmcp_agents config --file <path-to-config.yml>` to wrap an MCP Server. In addition to the `--file` option, you can also use `--bundled <server-name>` to wrap a bundled MCP Server, or `--url <url-to-config.yml>` to grab the configuration from a URL.

## Example Configuration

For a comprehensive example of the declarative configuration, please refer to the augmented version of Wrale's [`mcp-server-tree-sitter` MCP Server configuration file](./fastmcp_agents/bundled/servers/wrale_mcp-server-tree-sitter.yml). This bundled file serves as the primary example and demonstrates various configuration options.

```yaml
mcpServers:
  tree-sitter:
    command: uvx
    args:
      - mcp-server-tree-sitter

agents:
  - name: ask_tree_sitter
    description: >-
      Ask the tree-sitter agent to find items in the codebase. It can search for
      text, symbols, classes, functions, variables, and more. It can also find
      ...

    default_instructions: >-
      You are a helpful assistant that provides users a simple way to find items
      in their codebase. You will be given a codebase and you will need to use
      the tools available to you to find items in the codebase.
      ...

    blocked_tools:
      - clear_cache
      - remove_project_tool
      - diagnose_config
```

To invoke a bundled server, simply provide the provider and server name

```bash
uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter
```

To invoke a single tool call, you can use the `call` subcommand:

```bash
uvx fastmcp_agents \
config --bundled wrale_mcp-server-tree-sitter \
call ask_tree_sitter '{"instructions": "Analyze the codebase in . and tell me what you found."}' \
run
```