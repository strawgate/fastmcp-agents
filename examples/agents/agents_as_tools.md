


```python
from fastmcp_agents import FastMCPAgent
from fastmcp.tools import ToolManager
from fastmcp import FastMCP

# Create server
mcp = FastMCP("Echo Server")

servers = []
@mcp.tool()
def echo_tool(text: str) -> str:
    """Echo the input text"""
    return text


@mcp.resource("echo://static")
def echo_resource() -> str:
    return "Echo!"


@mcp.resource("echo://{text}")
def echo_template(text: str) -> str:
    """Echo the input text"""
    return f"Echo: {text}"


@mcp.prompt("echo")
def echo_prompt(text: str) -> str:
    return text

@mcp.tool()
def adder_agent(x: int, y: int) -> int:
    """Adds two numbers."""
    

@mcp.tool()
class AdderAgent(FastMCPAgent):
    """Adds two numbers."""

    def list_tools(self):
        return [
            Tool(
                name="Adder",
                description="Adds two numbers.",
            )
        ]


manager = ToolManager()
manager.add_tool_from_fn(Adder())
result = await manager.call_tool("Adder", {"x": 1, "y": 2})


```