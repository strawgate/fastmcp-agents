Why teach every Agent how to use every tool? Why put the instructions on how to run `git_clone` into every Agent you write? Why do you have to keep telling it that it cant clone with `depth: 0`?

What if you could embed an Expert user of the tools available on the Server, into the Server?

## Installation

For all of the following options start with:

1. [Install UV](https://docs.astral.sh/uv/getting-started/installation/)
2. Follow the instructions for configuring your preferred provider and model
3. Follow the instruction for your MCP Client (Web UI, IDE (VSCode, Roo Code), cli)

### Providers

#### Google Vertex AI

1. Set up your Google Vertex AI credentials. `gcloud init` should be your first option.
2. Set your model `export MODEL="vertex_ai/gemini-2.5-flash-preview-05-20"`

Alternatives to `gcloud init`:

1. [Create a service account](https://console.cloud.google.com/iam-admin/serviceaccounts/create) with `Vertex AI User` role
2. Download the credentials
3. Set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the path of the JSON key file

### MCP Clients 

In each of these examples we'll use the `wrale_mcp-server-tree-sitter` as our MCP Server.
Feel free to experiment with other MCP Servers.

#### CLI

1. Run `uvx run fastmcp_agents invoke agent "ask_tree_sitter" "can you lookup github issues?" --config-url "https://raw.githubusercontent.com/strawgate/fastmcp-agents/refs/heads/main/fastmcp_agents/servers/wrale_mcp-server-tree-sitter.yml"`

#### MCP Inspector

1. Run `npx @modelcontextprotocol/inspector uvx fastmcp_agents bundled server --agent-only wrale_mcp-server-tree-sitter`
2. Visit http://localhost:6274/#tools
3. Click `Connect` to connect to your MCP Server
4. Click `List Tools`
5. Click `ask_tree_sitter`
6. Interact with the tool via the instructions text area

#### Open Webui

1. Run open-webui.  This is the best way:
```
docker pull ghcr.io/open-webui/open-webui:main
docker rm -f open-webui
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui -e WEBUI_AUTH=false --restart always ghcr.io/open-webui/open-webui:main
```
2. Run mcpo and your MCP Server to provide an OpenAPI interface for open webui to use: `uvx mcpo --port 8000 -- uvx fastmcp_agents bundled server --agent-only wrale_mcp-server-tree-sitter`
3. Visit http://127.0.0.1:3000
4. Register your tool with open webui.  Click the account in the upper right and select `settings > tools > (+) add connection`.  Set the base url to http://localhost:8000 and click save.
5. 

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

With full flexibility for you to dynamically constrain the embedded Agent based on information provided by the caller.