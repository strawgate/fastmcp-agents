| Server | Agents |  MCP Inspector  | Direct CLI  | IDE / MCP Client    | Open WebUI |
|--------|------------|------------|------------|------------|------------|
| [Git (from Cyanheads)](#1-git-from-cyanheads) | [ask_git_agent](/src/fastmcp_agents/bundled/cyanheads_git-mcp-server.yml) | [🔎 Inspector](#11-run-with-mcp-inspector) | [Call Tools from CLI](#12-directly-call-tools-via-the-cli) | [mcpServers](#13-use-in-an-mcp-server-configuration) | [Open WebUI](#14-use-in-open-webui) |
| [Github](#2-github) | [ask_github_agent, summarize_github_issue, summarize_pull_request](/src/fastmcp_agents/bundled/github_github-mcp-server.yml) | [🔎 Inspector](#21-run-with-mcp-inspector) | [Call Tools from CLI](#22-directly-call-tools-via-the-cli) | [mcpServers](#23-use-in-an-mcp-server-configuration) | [Open WebUI](#24-use-in-open-webui) |
| [Tree Sitter](#3-tree-sitter) | [ask_tree_sitter_agent](/src/fastmcp_agents/bundled/wrale_mcp-server-tree-sitter.yml) | [🔎 Inspector](#31-run-with-mcp-inspector) | [Call Tools from CLI](#32-directly-call-tools-via-the-cli) | [mcpServers](#33-use-in-an-mcp-server-configuration) | [Open WebUI](#34-use-in-open-webui) |
| [MotherDuckDB](#4-motherduckdb) | [ask_duckdb_agent](/src/fastmcp_agents/bundled/motherduckdb_mcp-server-motherduck.yml) | [🔎 Inspector](#41-run-with-mcp-inspector) | [Call Tools from CLI](#42-directly-call-tools-via-the-cli) | [mcpServers](#43-use-in-an-mcp-server-configuration) | [Open WebUI](#44-use-in-open-webui) |
| [Git (from MCP)](#5-git-official-mcp-server) | [ask_git_agent](/src/fastmcp_agents/bundled/mcp_git.yml) | [🔎 Inspector](#51-run-with-mcp-inspector) | [Call Tools from CLI](#52-directly-call-tools-via-the-cli) | [mcpServers](#53-use-in-an-mcp-server-configuration) | [Open WebUI](#54-use-in-open-webui) |

# Running Bundled MCP Servers

## 1. Git (from Cyanheads)
A version of the [Cyanheads Git MCP server](https://github.com/cyanheads/git-mcp-server) that is wrapped with an agent and has improved descriptions and parameter names for the Git tools.

| Agent Name | Agent Description |
|------------|-------------------|
| `ask_git_agent` | Assists with performing Git operations as requested by the user. |

### 1.1 Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled cyanheads_git-mcp-server run`

### 1.2 Directly call tools via the CLI

```
uvx fastmcp_agents config --bundled cyanheads_git-mcp-server \
call ask_git_agent '{"task": "Clone the https://github.com/modelcontextprotocol/servers.git repository for me."}' \
run
```

### 1.3 Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "fastmcp_agents_git": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "cyanheads_git-mcp-server",
                "run"
            ]
        }
    }
}
```

### 1.4 Use in Open WebUI

Follow the instructions in [Open WebUI](../usage/web_ui.md) to run Open WebUI.

You can expose the server via mcpo:
```bash
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled cyanheads_git-mcp-server run
```

## 2. Github

A version of the [Github MCP server](https://github.com/github/github-mcp-server) that is wrapped with an agent and has improved descriptions and parameter names for the Github tools.

| Agent Name | Agent Description |
|------------|-------------------|
| `ask_github_agent` | Assists with performing GitHub operations as requested by the user. |
| `summarize_github_issue` | Assists with summarizing a GitHub issue and comments. |
| `summarize_pull_request` | Request a report on a GitHub pull request. |

### 2.1 Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled github_github-mcp-server run`

### 2.2 Directly call tools via the CLI

```bash
uvx fastmcp_agents config --bundled github_github-mcp-server \
call ask_github_agent '{"task": "Summarize issue #1 in the repository modelcontextprotocol/servers. Include any relevant comments and provide a clear overview of the issue's status and content."}' \
run
```

### 2.3 Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "fastmcp_agents_github": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "github_github-mcp-server",
                "run"
            ]
        }
    }
}
```

### 2.4 Use in Open WebUI

Follow the instructions in [Open WebUI](../usage/web_ui.md) to run Open WebUI.

You can expose the server via mcpo:
```bash
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled github_github-mcp-server run
```

## 3. Tree Sitter

A version of the [Tree Sitter MCP server](https://github.com/wrale/mcp-server-tree-sitter) that is wrapped with an agent and has improved descriptions and parameter names for the Tree Sitter tools.

| Agent Name | Agent Description |
|------------|-------------------|
| `ask_tree_sitter_agent` | Ask the tree-sitter agent to find items in the codebase. It can search for text, symbols, classes, functions, variables, and more. |

### 3.1 Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter run`

### 3.2 Directly call tools via the CLI

```
uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter \
call ask_tree_sitter_agent '{"task": "Tell me all the classes in the repository located in the current working directory."}' \
run
```

### 3.3 Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "fastmcp_agents_tree_sitter": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "wrale_mcp-server-tree-sitter",
                "run"
            ]
        }
    }
}
```

### 3.4 Use in Open WebUI

Follow the instructions in [Open WebUI](../usage/web_ui.md) to run Open WebUI.

You can expose the server via mcpo:
```bash
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter run
```

## 4. MotherDuckDB

A version of the [MotherDuckDB MCP server](https://github.com/motherduckdb/mcp-server-motherduck) that is wrapped with an agent and has improved descriptions and parameter names for the MotherDuckDB tools.

| Agent Name | Agent Description |
|------------|-------------------|
| `ask_duckdb_agent` | Ask the duckdb agent to work with an in-memory database on your behalf. |

### 4.1 Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled motherduckdb_mcp-server-motherduck run`

### 4.2 Directly call tools via the CLI

```bash
uvx fastmcp_agents config --bundled motherduckdb_mcp-server-motherduck \
call ask_duckdb_agent '{"task": "Create a table called 'users' with the following columns: id, name, email."}' \
run
```

### 4.3 Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "fastmcp_agents_motherduckdb": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "motherduckdb_mcp-server-motherduck",
                "run"
            ]
        }
    }
}
```

### 4.4 Use in Open WebUI

Follow the instructions in [Open WebUI](../usage/web_ui.md) to run Open WebUI.

You can expose the server via mcpo:
```bash
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled motherduckdb_mcp-server-motherduck run
```

## 5. Git (Official MCP Server)

A version of the [ModelContextProtocol Git MCP server](https://github.com/modelcontextprotocol/servers) that is wrapped with an agent and has improved descriptions and parameter names for the Git tools.

### 5.1 Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled mcp_git run`

### 5.2 Directly call tools via the CLI

```bash
uvx fastmcp_agents config --bundled mcp_git \
call ask_git_agent '{"task": "Show me the status of the repository."}' \
run
```

### 5.3 Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "fastmcp_agents_git": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "mcp_git",
                "run"
            ]
        }
    }
}
```

### 5.4 Use in Open WebUI

Follow the instructions in [Open WebUI](../usage/web_ui.md) to run Open WebUI.

You can expose the server via mcpo:
```bash
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled mcp_git run
```

### 6. DuckDuckGo (from nickclyde)

A version of the [DuckDuckGo MCP server](https://github.com/nickclyde/duckduckgo-mcp-server) that is wrapped with an agent.

| Agent Name | Agent Description |
|------------|-------------------|
| `duckduckgo_agent` | Assists with searching the web with the DuckDuckGo search engine. |

### 6.1 Run with MCP Inspector

`npx @modelcontextprotocol/inspector uv run fastmcp_agents config --bundled nickclyde_duckduckgo-mcp-server run`

### 6.2 Directly call tools via the CLI

```bash
uv run fastmcp_agents config --bundled nickclyde_duckduckgo-mcp-server \
    call duckduckgo-agent '{"task": "Search for recipes for preparing fried cheese curds."}' \
    run
```

Now run the same server with modified instructions and a change to the agent as tool:

```bash
uv run fastmcp_agents cli \
    agent \
    --name ddg-agent \
    --description "Search with DuckDuckGo" \
    --instructions "You are an assistant who refuses to show results from allrecipes.com.  " \
    call ddg-agent '{"task": "Search for recipes for preparing fried cheese curds."}' \
    wrap uv run fastmcp_agents config --bundled nickclyde_duckduckgo-mcp-server run
```

Close inspection will show that the search query changes from:

```
{'query': 'fried cheese curds recipes'}
```

to:

```
{'query': 'recipes for preparing fried cheese curds -site:allrecipes.com'}
```

### 6.3 Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "fastmcp_agents_duckduckgo": {
            "command": "uv",
            "args": [
                "run",
                "fastmcp_agents",
                "config", "--bundled", "nickclyde_duckduckgo-mcp-server",
                "run"
            ]
        }
    }
}
```

### 6.4 Use in Open WebUI

Follow the instructions in [Open WebUI](../usage/web_ui.md) to run Open WebUI.

You can expose the server via mcpo:
```bash
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled nickclyde_duckduckgo-mcp-server run
```
