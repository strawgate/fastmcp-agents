# Tool Transformer

This module provides the [`transform_tool`](src/fastmcp/contrib/tool_transformer/tool_transformer.py:110) function and related utilities to modify existing FastMCP tools. It allows for intercepting tool calls, altering their behavior by changing parameters, adding new parameters for hooks, and executing custom logic before or after the original tool execution.

This is a community-contributed module and is located in the `contrib` directory. Please refer to the main [FastMCP Contrib Modules README](../../contrib/README.md) for general information about contrib modules and their guarantees.

## Purpose

The Tool Transformer is useful for scenarios where you need to:
- Modify arguments of an existing tool (e.g., setting constant values, providing new defaults, changing descriptions).
- Add new parameters that are not passed to the original tool but are available to custom hook functions.
- Execute custom logic before a tool call (e.g., logging, input validation, conditional logic via `pre_call_hook`).
- Process the response from a tool before returning it (e.g., filtering, transforming, logging via `post_call_hook`).
- Load tool transformation configurations from YAML files.

## Installation

Since this is a contrib module, it is included with the FastMCP library. No separate installation is required.

## Core Concepts

### `transform_tool` Function
The primary way to use this module is through the [`transform_tool`](src/fastmcp/contrib/tool_transformer/tool_transformer.py:110) function. This function takes an existing `FastMCPTool` instance and an `FastMCP` server instance to which the new, transformed tool will be added. It allows you to specify a new name, description, parameter overrides, extra hook parameters, and pre/post call hooks.

### Parameter Overrides
You can modify existing parameters of a tool using the [`ToolParameterOverride`](src/fastmcp/contrib/tool_transformer/types.py:54) class. This allows you to:
- Change a parameter's description.
- Set a `constant` value for a parameter, which will always be used.
- Provide a new `default` value.
- Make an optional parameter `required` (note: you cannot make an already required parameter optional).

### Extra Hook Parameters
New parameters can be defined using [`ExtraParameterString`](src/fastmcp/contrib/tool_transformer/types.py:18), [`ExtraParameterNumber`](src/fastmcp/contrib/tool_transformer/types.py:11), or [`ExtraParameterBoolean`](src/fastmcp/contrib/tool_transformer/types.py:25). These parameters are exposed by the transformed tool but are *not* passed to the underlying original tool. Instead, their values are passed to the `pre_call_hook` and `post_call_hook` functions, allowing for more flexible hook logic.

### Pre-call and Post-call Hooks
- **`pre_call_hook`**: A callable (async function) that is executed *before* the original tool is called. It receives the arguments intended for the original tool (which can be modified) and the values of any `extra_parameters`. See [`PreToolCallHookProtocol`](src/fastmcp/contrib/tool_transformer/types.py:46).
- **`post_call_hook`**: A callable (async function) that is executed *after* the original tool returns a response. It receives the response from the original tool, the arguments that were passed to it, and the values of any `extra_parameters`. See [`PostToolCallHookProtocol`](src/fastmcp/contrib/tool_transformer/types.py:37).

### Loading Overrides from YAML
The module also supports defining tool transformations in YAML files. The [`loader.py`](src/fastmcp/contrib/tool_transformer/loader.py) provides:
- [`ToolOverrides`](src/fastmcp/contrib/tool_transformer/loader.py:13): A Pydantic model to parse YAML configurations for multiple tool overrides.
- [`transform_tools_from_server`](src/fastmcp/contrib/tool_transformer/loader.py:29): A function to apply transformations defined in a `ToolOverrides` object to all matching tools from a source server and add them to a target server.

## Usage

### Programmatic Transformation
To transform a single tool programmatically:
1. Obtain an instance of the tool you want to transform (e.g., from a `FastMCP` server).
2. Call the [`transform_tool`](src/fastmcp/contrib/tool_transformer/tool_transformer.py:110) function, providing the original tool, the target server, and any desired transformation options (name, description, overrides, hooks, etc.).

Refer to [`example-overrides.py`](src/fastmcp/contrib/tool_transformer/example-overrides.py) for transforming parameters and [`example-hooks.py`](src/fastmcp/contrib/tool_transformer/example-hooks.py) for using pre-call hooks.

### YAML-based Transformation
To transform multiple tools based on a YAML configuration:
1. Create a YAML file defining your tool overrides (see [`example-overrides-yaml.py`](src/fastmcp/contrib/tool_transformer/example-overrides-yaml.py) for structure).
2. Load this configuration using [`ToolOverrides.from_yaml()`](src/fastmcp/contrib/tool_transformer/loader.py:18) or [`ToolOverrides.from_yaml_file()`](src/fastmcp/contrib/tool_transformer/loader.py:23).
3. Use [`transform_tools_from_server`](src/fastmcp/contrib/tool_transformer/loader.py:29) to apply these transformations.

Refer to [`example-overrides-yaml.py`](src/fastmcp/contrib/tool_transformer/example-overrides-yaml.py) for a practical demonstration.

## Key Components and Parameters

### `transform_tool` Parameters:
- `tool`: The `FastMCPTool` instance to be transformed. (Required)
- `add_to_server`: The `FastMCP` server instance where the transformed tool will be added. (Required)
- `name`: The new name for the transformed tool. If `None`, the original tool's name is used. (Optional)
- `description`: The new description for the transformed tool. If `None`, the original tool's description is used. (Optional)
- `hook_parameters`: A list of `ExtraToolParameterTypes` ([`ExtraParameterString`](src/fastmcp/contrib/tool_transformer/types.py:18), [`ExtraParameterNumber`](src/fastmcp/contrib/tool_transformer/types.py:11), [`ExtraParameterBoolean`](src/fastmcp/contrib/tool_transformer/types.py:25)) objects. These define additional parameters for hooks. (Optional)
- `parameter_overrides`: A dictionary mapping existing parameter names to [`ToolParameterOverride`](src/fastmcp/contrib/tool_transformer/types.py:54) objects. (Optional)
- `pre_call_hook`: An async callable matching [`PreToolCallHookProtocol`](src/fastmcp/contrib/tool_transformer/types.py:46). Executed before the original tool call. (Optional)
    - Receives: `tool_args: dict[str, Any]` (modifiable), `hook_args: dict[str, Any]`
- `post_call_hook`: An async callable matching [`PostToolCallHookProtocol`](src/fastmcp/contrib/tool_transformer/types.py:37). Executed after the original tool call. (Optional)
    - Receives: `response: list[TextContent | ImageContent | EmbeddedResource]`, `tool_args: dict[str, Any]`, `hook_args: dict[str, Any]`

### `ToolParameterOverride` ([`types.py`](src/fastmcp/contrib/tool_transformer/types.py:54) inheriting from [`base.py`](src/fastmcp/contrib/tool_transformer/base.py:60)):
- `description`: New description for the parameter. (Optional)
- `constant`: A constant value for the parameter. If set, this value always overrides any input. (Optional)
- `default`: New default value for the parameter. (Optional)
- `required`: Boolean indicating if the parameter should be made required. Cannot make an already required parameter optional. (Optional)

### `ExtraToolParameterTypes` ([`types.py`](src/fastmcp/contrib/tool_transformer/types.py:32) inheriting from [`base.py`](src/fastmcp/contrib/tool_transformer/base.py:20)):
- These are [`ExtraParameterString`](src/fastmcp/contrib/tool_transformer/types.py:18), [`ExtraParameterNumber`](src/fastmcp/contrib/tool_transformer/types.py:11), [`ExtraParameterBoolean`](src/fastmcp/contrib/tool_transformer/types.py:25).
- `name`: Name of the extra parameter. (Required)
- `description`: Description of the extra parameter. (Required)
- `required`: Whether this extra parameter is required. (Required)
- `default`: Default value for the extra parameter. (Optional)
- `type`: Automatically set to "string", "number", or "boolean".

### `ToolOverrides` ([`loader.py`](src/fastmcp/contrib/tool_transformer/loader.py:13)):
- `tools`: A dictionary where keys are original tool names and values are [`ToolOverride`](src/fastmcp/contrib/tool_transformer/loader.py:56) objects.

### `ToolOverride` ([`loader.py`](src/fastmcp/contrib/tool_transformer/loader.py:56)):
- `name`: New name for the tool. (Optional)
- `description`: New description for the tool. (Optional)
- `parameter_overrides`: Dictionary of parameter overrides for this specific tool. (Optional)

## Examples
- **Parameter Overrides (Programmatic):** See [`example-overrides.py`](src/fastmcp/contrib/tool_transformer/example-overrides.py)
- **Pre-call Hooks:** See [`example-hooks.py`](src/fastmcp/contrib/tool_transformer/example-hooks.py)
- **Parameter Overrides (YAML):** See [`example-overrides-yaml.py`](src/fastmcp/contrib/tool_transformer/example-overrides-yaml.py)