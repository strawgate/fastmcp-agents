# Configuration File Reference

FastMCP-Agents configurations can be defined in YAML or JSON files. These files specify agents, wrapped MCP servers, and tool transformations. This document provides a reference for the structure and options available in configuration files.

## File Format

Configuration files can be either YAML or JSON.

## Top-Level Structure

A fastmcp-agents configuration file has the following top-level structure:

```yaml
# Example YAML Configuration File

agents:
  # List of agent definitions
  - name: "agent_name"
    # ... agent properties ...

mcpServers:
  # Dictionary of wrapped MCP server definitions
  server_name:
    # ... server properties ...
```

or

```json
// Example JSON Configuration File

{
  "agents": [
    // List of agent definitions
    {
      "name": "agent_name",
      // ... agent properties ...
    }
  ],
  "mcpServers": {
    // Dictionary of wrapped MCP server definitions
    "server_name": {
      // ... server properties ...
    }
  }
}
```

## `agents` Section

The `agents` section is an optional list of agent definitions. Each item in the list is an object with the following properties:

*   `name` (string, required): The unique name of the agent.
*   `description` (string, required): A brief description of the agent's purpose.
*   `instructions` (string, required): The default instructions provided to the LLM for this agent.
*   `allowed_tools` (list of strings, optional): A list of tool names that this agent is allowed to use. If not specified, the agent can use all available tools unless blocked.
*   `blocked_tools` (list of strings, optional): A list of tool names that this agent is explicitly prevented from using.

```yaml
agents:
  - name: "my_agent"
    description: "An agent for performing file operations."
    instructions: "Use the available tools to read and list files as requested."
    allowed_tools:
      - "read_file"
      - "list_files"
```

## `mcpServers` Section

The `mcpServers` section is an optional dictionary where keys are user-defined names for the wrapped MCP servers. Each value is an object defining a wrapped server with the following properties:

*   `command` (string, required): The executable command to run the MCP server.
*   `args` (list of strings, optional): A list of arguments to pass to the `command`.
*   `env` (dictionary, optional): A dictionary of environment variables to set for the server process.
*   `tools` (dictionary, optional): A dictionary for applying tool transformations to the tools exposed by this server. Keys are the original tool names, and values are tool transformation definitions.

```yaml
mcpServers:
  my_file_server:
    command: "uvx"
    args:
      - "filesystem-mcp-server"
      - "run"
    env:
      LOG_LEVEL: "INFO"
    tools:
      # Tool transformations for tools from this server
      read_file:
        description: "Read the content of a specified file."
        parameter_overrides:
          - name: "file_path"
            description: "The path to the file to read."
            required: true
```

## Tool Transformation Definition (within `mcpServers.tools`)

Within the `tools` section of an `mcpServers` definition, you can define transformations for individual tools. The key is the original tool name, and the value is an object with the following properties:

*   `description` (string, optional): A new description for the tool.
*   `parameter_overrides` (list of objects, optional): A list of parameter override definitions. Each object has:
    *   `name` (string, required): The name of the parameter to override.
    *   `description` (string, optional): A new description for the parameter.
    *   `required` (boolean, optional): Whether the parameter is required.
    *   `default` (any, optional): A default value for the parameter if not provided.
    *   `const` (any, optional): A constant value for the parameter, overriding any provided value.
*   `pre_call_hook` (string, optional): The name of an asynchronous Python function to run before the original tool call.
*   `post_call_hook` (string, optional): The name of an asynchronous Python function to run after the original tool call.

```yaml
mcpServers:
  my_server:
    command: "..."
    tools:
      some_tool:
        description: "An enhanced version of some_tool."
        parameter_overrides:
          - name: "input_param"
            description: "The main input for the tool."
            required: true
          - name: "optional_param"
            default: "default_value"
        pre_call_hook: "my_module.before_some_tool"
        post_call_hook: "my_module.after_some_tool"
```

Note that `pre_call_hook` and `post_call_hook` refer to Python functions that must be accessible in the environment where fastmcp-agents is running.

Configuration files provide a flexible and organized way to define your fastmcp-agents environment, making it easy to manage complex setups and share configurations.
