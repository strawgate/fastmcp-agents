# CLI Command Group

The `cli` command group allows you to build agents and wrap servers directly from the command line. Commands within this group can be chained.

## Basic Usage

```bash
uvx fastmcp_agents cli [COMMAND] [OPTIONS] [ARGUMENTS]
```

## Available Commands

| Command | Description |
|---------|-------------|
| `agent` | Build an agent over the command line. |
| `list` | List the tools available on the server. |
| `call` | Add a tool call to the pending tool calls list. |
| `wrap` | Take the last of the cli args and use them to run the mcp server and run it. |

### `agent`

Build an agent over the command line.

```bash
uvx fastmcp_agents cli agent [OPTIONS]
```

**Options:**
* `--name TEXT`: The name of the agent to wrap. (Required)
* `--description TEXT`: The description of the agent to wrap. (Required)
* `--instructions TEXT`: The instructions of the agent to wrap. (Required)
* `--allowed-tools TEXT`: A comma separated list of the tools that the agent can use.
* `--blocked-tools TEXT`: A comma separated list of the tools that the agent cannot use.

### `list`

List the tools available on the server.

```bash
uvx fastmcp_agents cli list
```

### `call`

Add a tool call to the pending tool calls list.

```bash
uvx fastmcp_agents cli call NAME PARAMETERS
```

**Arguments:**
* `NAME`: The name of the tool to call.
* `PARAMETERS`: A JSON string of the arguments for the tool call.

### `wrap`

Take the last of the cli args and use them to run the mcp server and run it.

```bash
uvx fastmcp_agents cli wrap [OPTIONS] DIRECT_WRAP_ARGS...
```

**Options:**
* `--env TEXT`: Environment variables to set for the server (can be used multiple times).

**Arguments:**
* `DIRECT_WRAP_ARGS...`: The command and arguments to run the MCP server.

## Examples

### Basic Agent Creation and Server Wrapping

```bash
uvx fastmcp_agents cli \
agent \
--name "ask_tree_sitter" \
--description "Ask the tree-sitter agent to find items in the codebase." \
--instructions "You are a helpful assistant that provides users a simple way to find items in their codebase." \
wrap uvx git+https://github.com/wrale/mcp-server-tree-sitter.git
```

### Multiple Agents with Tool Call

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
call learn_tree_sitter '{ "task": "Analyze the codebase in . and tell me what you found." }' \
wrap uvx git+https://github.com/wrale/mcp-server-tree-sitter.git
```

### Setting Environment Variables

```bash
uvx fastmcp_agents cli \
agent \
--name "my_agent" \
--description "My agent description" \
--instructions "My agent instructions" \
wrap \
--env "API_KEY=your_api_key" \
--env "DEBUG=true" \
your-server-command
```

## Best Practices

1. Use descriptive names and descriptions for your agents
2. Provide clear instructions for agent behavior
3. Explicitly list allowed and blocked tools when needed
4. Use environment variables for sensitive information
5. Chain commands logically for complex operations 