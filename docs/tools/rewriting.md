# Guide to Tool Rewriting in FastMCP-Agents

FastMCP-Agents provides powerful capabilities to modify the behavior and appearance of tools exposed by wrapped MCP servers. This process, which we refer to as "tool rewriting," is primarily achieved through the `transform_tool` function, which applies transformations defined by `ToolOverride` objects. This guide explores the two main aspects of tool rewriting: **Tool Overriding** and **Tool Wrapping**.

This guide provides an in-depth look at both methods, explaining when and how to use them effectively to tailor tools for your specific agent or application needs.

## Understanding Tool Rewriting

When you wrap a third-party MCP server with FastMCP-Agents, you gain the ability to intercept and modify the tool definitions and their execution. This is crucial for:

- **Improving Agent Usability:** Making tool descriptions and parameters clearer and more aligned with the agent's instructions.
- **Simplifying Tool Calls:** Setting default or constant values for parameters to reduce the complexity of tool calls for the agent.
- **Adding Custom Logic:** Executing code before or after a tool call to handle data transformation, logging, validation, or other custom operations.
- **Adapting Tools:** Modifying tool behavior to better fit the context of your agent or the overall workflow.

Tool rewriting is achieved through two distinct mechanisms: Tool Overriding and Tool Wrapping, both applied using the `transform_tool` function.

## Tool Overriding

Tool Overriding allows you to modify the *metadata* of a tool, such as its description, parameter names, descriptions, default values, and constant values. This is primarily a configuration-driven approach and can be done using Python code, YAML, or JSON configuration files.

The primary goal of overriding is to make the tool's interface more intuitive and predictable for the agent or the system interacting with it.

### When to Use Tool Overriding

- You need to clarify or change the description of a tool or its parameters.
- You want to set default values for optional parameters.
- You want to hardcode constant values for certain parameters that should not be determined by the agent.
- You need to rename parameters to be more descriptive or consistent.

### How to Use Tool Overriding

Tool overriding can be configured using Python, YAML, or JSON. The structure typically involves specifying the tool name and then providing the overrides for its properties or parameters.

#### Example: Overriding with YAML/JSON

This method is suitable when using configuration files to define your wrapped server. You specify overrides under a `tools` key, referencing the original tool name.

```yaml
tools:
  convert_time:
    description: >-
        An updated multi-line description
        for the time conversion tool.
    parameter_overrides:
      # Override the 'source_timezone' parameter
      - name: source_timezone
        description: The timezone the input time is currently in. Defaults to America/New_York.
        constant: America/New_York # Set a constant value

      - name: time
        description: The time string to convert (e.g., "3:00 PM").
        default: "3:00" # Set a default value
```


In these examples, the `convert_time` tool's description is updated, and its `source_timezone` parameter is given a new description and a constant value, while the `time` parameter gets a new description and a default value.

#### Example: Overriding with Python

When configuring server wrapping programmatically with Python, you use the `transform_tool` function, providing a `ToolOverride` object or keyword arguments that define the overrides.

```python
from fastmcp import FastMCP
from fastmcp_agents.vendored.tool_transformer import transform_tool, ToolOverride, StringToolParameter

# Assuming 'original_tool_definition' is the definition of the tool
# and 'frontend_server' is the server object

override = ToolOverride(
        name="convert_time_nyc", # Optionally rename the tool
        description="Converts a time from New York to another timezone.",
        parameter_overrides=[
            StringToolParameter(
                name="source_timezone",
                description="The timezone the input time is currently in. This is fixed to New York.",
                constant="America/New_York" # Set a constant value
            ),
            StringToolParameter(
                name="time",
                description="The time string to convert (e.g., \"3:00 PM\").",
                default="3:00" # Set a default value
            )
        ]
    )

transformed_tool = override.apply_to_tool(original_tool_definition)

# Add the transformed_tool to your FastMCP server instance
# frontend_server.add_tool(transformed_tool)
```

Using Python provides more flexibility, allowing for dynamic overrides based on other logic if needed. The transformed tool can then be added to a FastMCP server.

## Tool Wrapping

Tool Wrapping allows you to execute custom Python code *before* (`pre_call_hook`) or *after* (`post_call_hook`) an original tool call. This is a more powerful method than overriding, enabling complex data transformations, conditional logic, external API calls, or logging around the original tool's execution.

### When to Use Tool Wrapping

- You need to transform input arguments before they are passed to the original tool.
- You need to process or transform the output of the original tool before returning it.
- You need to add logging or monitoring around tool calls.
- You need to implement conditional logic that affects whether or how the original tool is called.
- You need to call external services or perform side effects before or after the tool execution.

### How to Use Tool Wrapping

Tool wrapping is typically done using Python code, leveraging the `transform_tool` function provided by FastMCP-Agents. You define asynchronous Python functions (`pre_call_hook` and `post_call_hook`) that will be executed at the appropriate times.

```python
from fastmcp_agents.vendored.tool_transformer import transform_tool

async def pre_call_hook(tool_call_kwargs):
    """
    This function is executed before the original tool is called.
    It receives the keyword arguments that will be passed to the tool.
    You can modify tool_call_kwargs in place.
    """
    print(f"Executing pre-call hook for tool: {original_tool_definition.name}")
    print(f"Original arguments: {tool_call_kwargs}")

    # Example: Add a default unit if not provided
    if 'unit' not in tool_call_kwargs or tool_call_kwargs['unit'] is None:
        tool_call_kwargs['unit'] = 'fahrenheit'
        print(f"Added default unit: {tool_call_kwargs['unit']}")

    # Example: Perform validation
    if 'location' in tool_call_kwargs and not isinstance(tool_call_kwargs['location'], str):
        raise ValueError("Location must be a string.")

    # You can also return a modified dictionary, but modifying in place is common
    # return tool_call_kwargs

async def post_call_hook(tool_call_result):
    """
    This function is executed after the original tool has been called.
    It receives the result returned by the original tool.
    You can process or transform the result before it's returned to the agent.
    """
    print(f"Executing post-call hook for tool: {original_tool_definition.name}")
    print(f"Original result: {tool_call_result}")

    # Example: Add a custom message to the result
    if isinstance(tool_call_result, dict):
        tool_call_result['processed_by_agent'] = True
        print("Added 'processed_by_agent' flag to result.")

    # Example: Handle errors or specific result values
    # if tool_call_result.get('status') == 'error':
    #     print("Tool call resulted in an error.")

    return tool_call_result # Return the processed result

wrapped_tool = transform_tool(
    original_tool_definition,
    # frontend_server, # The server the tool belongs to - Removed as transform_tool doesn't take a server
    name="get_weather_enhanced", # Give the wrapped tool a new name
    description="Gets the weather with enhanced pre/post processing.",
    pre_call_hook=pre_call_hook,
    post_call_hook=post_call_hook
)

# Add the wrapped_tool to your wrapped server's tool list
# wrapped_server.add_tool(wrapped_tool)
```

In this example, the `pre_call_hook` checks for a missing 'unit' parameter and adds a default, and also performs basic validation on the 'location' parameter. The `post_call_hook` adds a flag to the result dictionary.

## Combining Overriding and Wrapping

You can combine tool overriding and wrapping when using the Python configuration method. This allows you to modify both the tool's metadata and its execution logic within a single transformation.

```python
from fastmcp_agents.vendored.tool_transformer import transform_tool

# Assuming 'original_tool_definition' is the definition of the tool
# and 'frontend_server' is the server object

async def pre_call_hook_combined(tool_call_kwargs):
    print("Combined pre-call hook.")
    # ... custom logic ...

async def post_call_hook_combined(tool_call_result):
    print("Combined post-call hook.")
    # ... custom logic ...
    return tool_call_result

combined_tool = transform_tool(
    original_tool_definition,
    # frontend_server, # The server the tool belongs to - Removed as transform_tool doesn't take a server
    name="enhanced_and_overridden_tool",
    description="This tool has both metadata overrides and execution hooks.",
    parameter_overrides=[
        {
            "name": "some_parameter",
            "description": "An overridden parameter description."
        }
    ],
    pre_call_hook=pre_call_hook_combined,
    post_call_hook=post_call_hook_combined
)

# Add the combined_tool to your wrapped server's tool list
# wrapped_server.add_tool(combined_tool)
