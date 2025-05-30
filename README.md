- Are you tired of teaching every Agent how to use every tool? 
- Why put the instructions on how to run `git_clone` into every Agent you write? 
- Why do you have to keep telling it that it cant clone with `depth: 0`?

FastMCP-Agents is a framework for building Agents into yours and more importantly, other people's MCP Servers!

## How's it work?!

Just take any third-party MCP Server and add just one extra tool -- an embedded Agent that can use the tools the server provides!

Simply take your existing MCP Server 
```bash
"mcp-server-tree-sitter": {
  "command": "uvx",
  "args": ["mcp-server-tree-sitter"]
}
```

And wrap it with an Agent:

```json
"github_github-mcp-server": {
  "command": "uvx",
  "args": [
    "fastmcp_agents", "cli",
    "agent",
    "--name","ask_tree_sitter",
    "--description", "Ask the tree-sitter agent to find items in the codebase.",
    "--instructions", "You are a helpful assistant that provides users a simple way to find items in their codebase.",
    "wrap", "uvx", "mcp-server-tree-sitter"
  ]
}
```

There's more than just adding an AI Agent in FastMCP-Agents.  You can also modify the tools and parameters of the server to make it easier for the Agent to use.

You can use FastMCP-Agents to wrap any MCP Server via the command line, configure the transformation with a YAML or JSON file, or even write Python code to configure the transformations!

| Option | Agents | Servers | Override Tools | Wrap Tools |
|--------|--------|---------|----------------|------------|
| [Python](./docs/wrapping/code.md) | ∞ | ∞ | Yes | Yes | 
| [YAML or JSON](./docs/wrapping/config.md) | ∞ | ∞ | Yes | No | 
| [Command-line](./docs/wrapping/cli.md) | ∞ | 1 | No | No |

## Example Servers

Here are some example servers that you can use to get started.  You can find the full list of bundled servers [here](./docs/bundled/servers.md).


## Using FastMCP-Agents as a CLI or MCP Server

For all of the following options start with:

1. [Install UV](https://docs.astral.sh/uv/getting-started/installation/)
2. Follow the instructions for configuring your preferred provider and model
3. Follow the instruction for your MCP Client (Web UI, IDE (VSCode, Roo Code), cli)

### Providers

#### Google Gemini

1. Set up your Google Gemini credentials. `gcloud init` should be your first option.
2. export MODEL="gemini/gemini-2.5-flash-preview-05-20"

Alternatives to `gcloud init`:
1. [Create a gemini api key](https://aistudio.google.com/app/apikey)
2. export GEMINI_API_KEY=your-gemini-api-key

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

#### CLI Tool Call Example

```bash
uvx fastmcp_agents cli \
agent \
--name "ask_tree_sitter" \
--description "Ask the tree-sitter agent to find items in the codebase." \
--instructions "You are a helpful assistant that provides users a simple way to find items in their codebase." \
call "ask_tree_sitter" "{\"instructions\": \"Analyze the codebase in . and tell me what you found.\"}" \
wrap uvx git+https://github.com/wrale/mcp-server-tree-sitter.git
```

#### MCP Inspector

1. Run `npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter`
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
2. Run mcpo and your MCP Server to provide an OpenAPI interface for open webui to use: `uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter`
3. Visit http://127.0.0.1:3000
4. Register your tool with open webui.  Click the account in the upper right and select `settings > tools > (+) add connection`.  Set the base url to http://localhost:8000 and click save.
