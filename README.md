Why teach every Agent how to use every tool? Why put the instructions on how to run `git_clone` into every Agent you write? Why do you have to keep telling it that it cant clone with `depth: 0`?

What if you could embed an Expert user of the tools available on the Server, into the Server?

## Adding FastMCP Agents to your MCP Server

FastMCP Agents is a framework for building Agents into FastMCP Servers.

Instead of building an MCP server, exposing dozens or hundreds of generic tools, and then expecting your consumers to figure out how to use them, you can embed an optional AI Agent directly into your MCP Server that can take plain language asks from a user or another AI Agent and implement them leveraging the available tools:

```python
web_agent = FastMCPAgent(
    name="Filesystem Agent",
    description="Assists with locating, categorizing, searching, reading, or writing files on the system.",
    default_instructions="""
    When you are asked to perform a task that requires you to interact with local files, 
    you should leverage the tools available to you to perform the task. If you are asked a
    question, you should leverage the tools available to you to answer the question.
    """,
    llm_link=AsyncLitellmLLMLink.from_model(
        model="vertex_ai/gemini-2.5-flash-preview-05-20",
    ),
)

web_agent.register_as_tools(server)
```

With full flexibility for you to dynamically constrain the embedded Agent based on information provided by the caller:

```python
def ask_about_issue(ctx: Context, issue_number: int) -> str:
    """Ask about an issue in the repository."""
    
    def get_relevant_issue(issue_number: int) -> str:
        """Get the relevant issue from the repository."""
        return github.get_issue(issue_number)
    
    Tool.from_function(
        name="get_relevant_issue",
        description="Get the relevant issue from the repository.",
        function=get_relevant_issue,
    )

   return issue_agent.run(
        issue_number=issue_number,
        instructions="""
        You are an expert at triaging GitHub issues.
        """,
        tools=[get_relevant_issue],
    )
```

## Adding FastMCP Agents to other people's MCP Servers

You can wrap any existing MCP Server and embed an AI Agent into the server, so that it can be used as a tool by other Agents. Combined with https://github.com/jlowin/fastmcp/pull/599 this enables entirely new ways of using MCP. 

For example, you can take the upstream GitHub MCP Server, improve any tool's description, name, add safeguards, set default parameters on `page_size`, limit response sizes, etc and expose it as a new MCP Server.

In 

```python
third_party_mcp_config = {
    "time": {
        "command": "uvx",
        "args": [
            "git+https://github.com/modelcontextprotocol/servers.git@2025.4.24#subdirectory=src/time",
            "--local-timezone=America/New_York",
        ],
    }
}

override_config_yaml = ToolOverrides.from_yaml("""
tools:
  search_issues:
    description: >-
        An updated multi-line description 
        for the search_issues tool.
    parameter_overrides:
      query:
        description: The query to search for issues.
        default: "is:open"
""")


async def async_main():
    async with Client(third_party_mcp_config) as remote_mcp_client:
        proxied_mcp_server = FastMCP.as_proxy(remote_mcp_client)

        frontend_server = FastMCP("Frontend Server")

        def limit_response_size(response: str) -> str:
            """Limit the response size to 1000 characters."""
            raise ValueError("Response size is too large.")

        await transform_tools_from_server(
            proxied_mcp_server,
            frontend_server,
            overrides=override_config_yaml,
            post_call_hooks=[limit_response_size],
        )

        github_agent = FastMCPAgent(
            name="GitHub Agent",
            description="Assists with GitHub-related tasks like searching issues, PRs, and more.",
            default_instructions="""
            You are an expert at triaging GitHub issues...
            """,
            llm_link=AsyncLitellmLLMLink.from_model(
                model=os.env("FASTMCP_AGENTS_DEFAULT_MODEL"),
            ),
        )

        github_agent.register_as_tools(frontend_server)

        await frontend_server.run_async(transport="sse")
```