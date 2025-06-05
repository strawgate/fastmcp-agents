# Agent Types and Concepts

FastMCP-Agents provides a flexible framework for building AI agents that can interact with MCP servers and their tools. This document describes the core agent types and concepts that are fundamental to developing agents with FastMCP-Agents.

The following diagram illustrates the inheritance hierarchy of the core agent types:

```mermaid
graph LR
    SingleStepAgent --> MultiStepAgent;
    MultiStepAgent --> FastMCPAgent;
    FastMCPAgent --> *FastMCPAgent;
```
## Core Agent Types

FastMCP-Agents provides several base classes for creating agents, each offering different levels of functionality and complexity:

### `SingleStepAgent`

The `SingleStepAgent` is the most basic agent type. It is designed to perform a single interaction with the LLM and execute the resulting tool calls. It does not manage conversation history across multiple turns.

*   **Key Characteristics:**
    *   Performs a single LLM call per invocation.
    *   Executes tool calls requested by the LLM in that single turn.
    *   Does not maintain conversation history internally.
    *   Suitable for simple tasks that can be completed in one turn.

*   **Core Methods:**
    *   `__init__`: Initializes the agent with a name, description, LLM link, system prompt, and default tools.
    *   `call_tool`: Executes a single tool call request.
    *   `call_tools`: Executes a list of tool call requests.
    *   `pick_tools`: Sends a prompt to the LLM and gets back tool call requests.
    *   `run_step`: Orchestrates a single step of the agent (picking tools and calling them).

### `MultiStepAgent`

The `MultiStepAgent` extends `SingleStepAgent` by adding the capability to manage conversation history and execute multiple steps (turns) with the LLM. This allows for more complex tasks that require a back-and-forth interaction.

*   **Key Characteristics:**
    *   Maintains conversation history using a memory implementation.
    *   Can execute multiple steps with the LLM until a task is completed or a step limit is reached.
    *   Includes built-in mechanisms for the LLM to report task success or failure.
    *   Suitable for tasks requiring iterative refinement or multiple tool interactions.

*   **Core Methods:**
    *   `__init__`: Initializes the agent with memory factory, max parallel tool calls, and step limit in addition to `SingleStepAgent` parameters.
    *   `run_steps`: Executes the multi-step process, managing the conversation and calling `run_step` for each turn.
    *   `run`: The main entry point for running the multi-step agent.
    *   `_prepare_conversation`: Initializes or retrieves the conversation history.

### `FastMCPAgent`

The `FastMCPAgent` is a concrete implementation of `MultiStepAgent` that provides default configurations for LLM link, memory, and other parameters, making it easier to get started with a multi-step agent.
