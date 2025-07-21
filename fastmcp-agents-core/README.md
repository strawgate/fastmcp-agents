# [FastMCP](https://github.com/jlowin/fastmcp) 🚀 Agents 🤖

FastMCP Agents bridges the gap between the generic tools in MCP servers and the specialized tools you need to solve your problem and gives you a straight-forward way to manage tool sprawl:
1. It turns generic tools in any MCP server into specialized tools that you can use anywhere
2. It can (optionally) embed an expert Agent into any MCP server

Whether you wrote the MCP server or GitHub did, FastMCP Agents can "wrap" any MCP server.

## Give me an example!

[Nick Clyde has a great DuckDuckGo MCP server](https://github.com/nickclyde/duckduckgo-mcp-server). So let's take his MCP Server and embed an Agent into it, let's make that Agent never return results from `allrecipes.com`. For the following example, you do not need to clone this repository:

```bash
export MODEL="gemini/gemini-2.5-flash-preview-05-20"
export GEMINI_API_KEY="abc123"
```
Or if you're logged into Google Cloud (via `gcloud init`), you can use the following:
```bash
export MODEL="vertex_ai/gemini-2.5-flash-preview-05-20"
```

(Note Gemini is not required -- you can provide any litellm model here with the provider auth as long as the model supports mandatory tool calling.)

```bash
uvx fastmcp_agents cli \
    agent \
    --name duckduckgo_agent \
    --description "Search with DuckDuckGo" \
    --instructions "You are an assistant who refuses to show results from allrecipes.com.  " \
    call duckduckgo_agent '{"task": "Search for recipes for preparing fried cheese curds. Tell me what makes each one special."}' \
    wrap uvx git+https://github.com/nickclyde/duckduckgo-mcp-server.git@d198a2f0e8bd7c862d87d8517e1518aa295f8348

Here are some recipes for preparing fried cheese curds:
Homemade Culver's Recipe from CopyKat Recipes: https://copykat.com/culvers-fried-cheese-curds/
Food Network: https://www.foodnetwork.com/recipes/amanda-freitag/fried-cheese-curds-31689 39
House of Nash Eats: https://houseofnasheats.com/fried-cheese-curds/
....
```

## How do I use it?

Follow our [quickstart guide](./docs/quickstart.md) to get started.

## Why Agents as Tools?

**Bad Tools make bad Agents**

Every MCP Server has a set of tools. It's up to the AI Agent to figure out, based on the provided names, descriptions, and arguments for the tools, how to leverage them to solve the user's question. When there's a problem with the instructions, the AI Agent's performance suffers.

**Generic Tools are Bad Tools**

With MCP, you run around and hook in all of these generic Tools to your various AI Agents and you let the AI Agent decide which ones are the right ones. A simple 3 MCP Server workflow can easily have 100+ tools. Each one is a shiny distraction on the path to solving the user's problem. These tools do almost the right thing almost most of the time.

**Specialized Tools don't scale**

So like me, you decide that your AI Agents shouldn't have 100 tools, they should only know about the exact tools they need to complete the task at hand. So you give up on MCP servers, write all your own tools.

## How's it work?!

Simply take your existing MCP Server 
```json
"mcp-server-tree-sitter": {
  "command": "uvx",
  "args": ["mcp-server-tree-sitter"]
}
```

And wrap it with an Agent:

```json
"mcp-server-tree-sitter": {
  "command": "uvx",
  "args": [
    "fastmcp_agents", "cli",
    "agent",
    "--name","ask_tree_sitter",
    "--description", "Ask the tree-sitter agent to find items in the codebase.",
    "--instructions", "You are a helpful assistant that provides users a simple way to find items in their codebase.",
    "wrap", 
    "uvx", "mcp-server-tree-sitter"
  ]
}
```
