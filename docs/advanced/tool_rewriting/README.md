# Wrapping Tools: Tool Transformation and Rewriting

FastMCP-Agents offers powerful capabilities to customize the tools exposed by wrapped MCP servers. This process, known as "tool rewriting" or "tool transformation," allows you to modify tool metadata and behavior to better suit your agents' needs. This tutorial explores how to transform and rewrite tools.

## Why Transform Tools?

Transforming tools is essential for several reasons:

*   **Improve Agent Interaction:** By clarifying tool descriptions and parameter names, you make it easier for the LLM to understand how to use the tools effectively.
*   **Simplify Tool Usage:** You can set default or constant values for parameters, reducing the complexity of tool calls that the agent needs to generate.
*   **Add Custom Logic:** You can inject custom Python code to run before or after a tool call, enabling data manipulation, validation, logging, or integration with other services.
*   **Adapt Tools to Context:** You can modify tool behavior to align with the specific requirements of your agent or the overall workflow.

## Aspects of Tool Rewriting

Tool rewriting in fastmcp-agents primarily involves two aspects: **Tool Overriding** and **Tool Wrapping**.

### 1. Tool Overriding

Tool Overriding focuses on modifying the *metadata* of a tool. This includes changing its name, description, parameter names, descriptions, required status, default values, and constant values. This is often a declarative process using configuration.

**When to Use Overriding:**

*   You need to improve the clarity of tool or parameter descriptions for the LLM.
*   You want to set default values for optional parameters.
*   You need to fix a parameter value to a constant.
*   You want to rename tools or parameters for consistency or clarity.

**Example: Overriding with YAML Configuration**

You can define tool overrides directly in your fastmcp-agents configuration file. Here's an example demonstrating how to override the `register_project_tool` from a hypothetical tree-sitter server:

```yaml
tools:
  register_project_tool:
    description: >-
      Register a new project for analysis. This tool must be called before any
      other project-related tools can be used. The project name will be used
      for all subsequent tool calls.
    parameter_overrides:
      - name: name
        description: The name of the project to register. All further calls that take a project name will be made using the value provided in this parameter. A good name is typically the name of the project directory.
        required: true
```

In this YAML snippet, we are overriding the description of the `register_project_tool` and providing a more detailed description for its `name` parameter, also marking it as required.

**Example: Overriding with Python**

When configuring your agents and servers programmatically with Python, you use the `ToolOverride` class and the `transform_tool` function:

```python
from fastmcp_agents.vendored.tool_transformer import transform_tool, ToolOverride, StringToolParameter

# Define the override using ToolOverride
override = ToolOverride(
    name="register_project_tool",
    description="Register a new project for analysis. This tool must be called before any other project-related tools can be used.",
    parameter_overrides=[
        StringToolParameter(
            name="name",
            description="The name of the project to register. All further calls that take a project name will be made using the value provided in this parameter.",
            required=True
        )
    ]
)

# Apply the override to the original tool definition
# original_tool_definition would be the tool object obtained from the wrapped server
transformed_tool = override.apply_to_tool(original_tool_definition)
```

### 2. Tool Wrapping

Tool Wrapping allows you to execute custom Python code *before* (`pre_call_hook`) or *after* (`post_call_hook`) the original tool call. This is useful for implementing dynamic behavior, data transformations, or side effects around the tool's execution.

**When to Use Wrapping:**

*   You need to modify the input arguments before they are passed to the original tool.
*   You need to process or transform the output of the original tool.
*   You want to add logging, monitoring, or validation logic around tool calls.
*   You need to perform actions (like calling external services) before or after the tool runs.

**Example: Wrapping a Tool with Hooks**

You define asynchronous Python functions to act as pre and post-call hooks. These functions are then passed to the `transform_tool` function.

```python
import asyncio
from datetime import datetime
from fastmcp_agents.vendored.tool_transformer import transform_tool

async def pre_call_hook(tool_call_kwargs: dict):
    """
    This function is executed before the original tool is called.
    It receives the keyword arguments that will be passed to the tool.
    You can modify tool_call_kwargs in place.
    """
    print(f"Pre-call hook: Processing arguments for tool call.")

    # Example: Normalize a parameter
    if 'project_name' in tool_call_kwargs and isinstance(tool_call_kwargs['project_name'], str):
        tool_call_kwargs['project_name'] = tool_call_kwargs['project_name'].strip().lower()

    # You can also perform validation or add default values here
    # if 'optional_param' not in tool_call_kwargs:
    #     tool_call_kwargs['optional_param'] = 'default_value'

    # Note: You don't typically return from a pre-call hook unless raising an exception

async def post_call_hook(tool_call_result: Any):
    """
    This function is executed after the original tool has been called.
    It receives the result returned by the original tool.
    You can return a modified result.
    """
    print(f"Post-call hook: Processing result.")

    # Example: Add metadata to the result if it's a dictionary
    if isinstance(tool_call_result, dict):
        tool_call_result['processed_timestamp'] = datetime.now().isoformat()
        tool_call_result['processed_by_agent'] = 'my_agent_v1'

    return tool_call_result # Return the (potentially modified) result

# Apply the wrapping using transform_tool
# original_tool_definition would be the tool object obtained from the wrapped server
wrapped_tool = transform_tool(
    original_tool_definition,
    name="enhanced_tool_with_hooks", # You can also rename the tool
    description="Enhanced version of the original tool with pre/post processing.",
    pre_call_hook=pre_call_hook,
    post_call_hook=post_call_hook
)
```

### Combining Overriding and Wrapping

When using Python for configuration, you can combine both tool overriding and wrapping in a single `transform_tool` call by providing both `ToolOverride` parameters (like `name`, `description`, `parameter_overrides`) and the `pre_call_hook` and `post_call_hook` functions.

```python
import asyncio
from datetime import datetime
from fastmcp_agents.vendored.tool_transformer import transform_tool, ToolOverride, StringToolParameter

# Define the override details
override_name = "combined_enhanced_tool"
override_description = "Tool with both metadata overrides and execution hooks."
parameter_overrides = [
    StringToolParameter(
        name="input_data",
        description="The data to be processed by the tool.",
        required=True
    )
]

# Define the hooks (same as in the Tool Wrapping example)
async def pre_call_hook(tool_call_kwargs: dict):
    print("Pre-call hook: Processing arguments in combined transformation.")
    # ... (logic to modify tool_call_kwargs)
    return tool_call_kwargs # Explicitly return tool_call_kwargs from pre-call hook

async def post_call_hook(tool_call_result: Any):
    print("Post-call hook: Processing result in combined transformation.")
    # ... (logic to modify tool_call_result)
    return tool_call_result # Return the (potentially modified) result

# Combine both approaches in a single transform_tool call
# original_tool_definition would be the tool object obtained from the wrapped server
combined_tool = transform_tool(
    original_tool_definition,
    name=override_name,
    description=override_description,
    parameter_overrides=parameter_overrides,
    pre_call_hook=pre_call_hook,
    post_call_hook=post_call_hook
)
```

By leveraging tool transformation and rewriting, you can significantly enhance the usability and functionality of the tools available to your fastmcp-agents agents, tailoring them precisely to your application's needs.
