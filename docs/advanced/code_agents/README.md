# Building Agents: Creating Your Own `as code` Agent

This tutorial will guide you through the process of creating a simple multi-step AI agent using the fastmcp-agents framework. We will use the `FastMCPAgent` class, which provides a convenient starting point with sensible defaults for LLM integration and memory management.

## Prerequisites

Before you begin, ensure you have followed the [Installation and Setup](../../quickstart.md) tutorial and configured your [LLM Provider](../../quickstart.md#configuring-your-provider-and-model).

## Steps

1.  **Import necessary classes:**
    You'll need to import the `FastMCPAgent` class and create an instance of it, providing a name, description, and instructions.

    ```python
    from fastmcp_agents.agent import FastMCPAgent

    agent = FastMCPAgent(
        name="my_example_agent",
        description="A simple example agent created for the tutorial.",
        instructions="You are a helpful assistant that responds to user messages.",
    )
    ```

2.  **Run the agent:**
    You can run the agent by calling its `curate` method with a user message. Since agents are asynchronous, you'll need to run this within an `asyncio` event loop.

    ```python
    async def main():
        user_message = "Hello, agent! How are you today?"
        response = await agent.curate(user_message)
        print(f"Agent Response: {response.content}")

    if __name__ == "__main__":
        # Ensure your LLM provider environment variables are set (e.g., MODEL)
        # os.environ["MODEL"] = "gemini/gemini-2.5-flash-preview-05-20" # Example if not set externally

        asyncio.run(main())
    ```

3.  **Hooking it into FastMCP**: 

Here is the complete code for creating and running a simple agent with FastMCP:

```python
import asyncio
import os

from fastmcp import FastMCP
from fastmcp_agents.agent import FastMCPAgent

server = FastMCP("Server")

agent = FastMCPAgent(
    name="my_example_agent",
    description="A simple example agent created for the tutorial.",
    instructions="You are a helpful assistant that responds to user messages.",
)

tool = FunctionTool.from_function(
    fn=agent.currate,
    name=agent.name,
    description=agent.description,
)

server.run()
```

Save this code as a Python file (e.g., `my_agent.py`), ensure your LLM provider environment variables are set, and run it using `python my_agent.py`.