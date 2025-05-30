

# Publishing Agents as Tools

work in progress

```python

from fastmcp import Client, StdioMCPServer
from fastmcp_agents import FastMCPAgent, transform_tool

wrapping = Client()

# avoiding async setup code but you want this to be async

wrapped = StdioMCPServer(
    command="uvx",
    args=["mcp-server-tree-sitter"],
)

backend = Client(wrapped)

def tool(str: test):
    return "Hello, world!"

agent = FastMCPAgent(
    name="My Agent",
    description="My Agent Description",
    instructions="My Agent Instructions",
    tools=[tool],
)

frontend = FastMCP("My MCP Server")

agent.register_as_tools(frontend)

frontend.run_async()
```

# Using Agents as Tools
# Publishing Agents as Tools

```python

from fastmcp import Client, StdioMCPServer
from fastmcp_agents import FastMCPAgent, transform_tool

wrapping = Client()

# avoiding async setup code but you want this to be async

wrapped = StdioMCPServer(
    command="uvx",
    args=["mcp-server-tree-sitter"],
)

backend = Client(wrapped)

agent = FastMCPAgent(
    name="My Agent",
    description="My Agent Description",
    instructions="My Agent Instructions",
)

frontend = FastMCP("My MCP Server")

def search_ast_nodes(project_id: str, query: str) -> list[str]:
    return ["fake","implementation"]

@frontend.tool()
async def just_a_tool(project_id: str, query: str) -> list[str]:
    return search_ast_nodes(project_id, query)

@frontend.tool()
async def tool_but_secretly_agent(repo_id: str, query: str) -> DesiredResponseModel:

    async def restricted_tool(query: str) -> list[str]:
        return search_ast_nodes(repo_id, query)

    Tool.from_function(
        restricted_tool,
        parameters=DesiredResponseModel.model_json_schema(),
    )

    return await agent.arun(f"Perform a special task that only makes sense with these two arguments and a tool: {repo_id} and {query}", tools=[restricted_tool], response_model=DesiredResponseModel)

frontend.add_tool(tool_but_secretly_agent)

frontend.run_async()
```

