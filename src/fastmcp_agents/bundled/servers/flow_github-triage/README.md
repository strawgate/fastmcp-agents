A GitHub Triage Agent that can be used to triage GitHub issues and pull requests.

| Agent Name | Agent Description |
|------------|-------------------|
| `triage_github_feature_request` | Triage a GitHub feature request. |
| `triage_github_bug_report` | Triage a GitHub bug report. |
| `investigate_github_issue` | Investigate a GitHub issue. |
| `propose_solution_for_github_issue` | Propose a solution for a GitHub issue. |
| `perform_pr_code_review` | Perform a code review of a pull request. |
| `update_pr_with_code_or_docs` | Update a pull request with code changes or documentation changes. |

# Usage
1. [Run with MCP Inspector](#run-with-mcp-inspector)
2. [Directly call tools via the CLI](#directly-call-tools-via-the-cli)
3. [Use in an MCP Server configuration](#use-in-an-mcp-server-configuration)
4. [Use in Open WebUI](#use-in-open-webui)

## Run with MCP Inspector

`npx @modelcontextprotocol/inspector uvx fastmcp_agents config --bundled flow_github-triage run`

When you setup the Inspector for the first time the timeout will default to 10s. Ensure you modify this to 120s or more under "Configuration" > "Request Timeout" in MCP Inspector.

## Directly call tools via the CLI

```bash
uvx fastmcp_agents config --bundled flow_github-triage \
call triage_github_feature_request '{"task": "Create a new file called 'test.txt' in the current directory."}' \
run
```

## Use in an MCP Server configuration

```json
{
    "mcpServers": {
        "augmented_github": {
            "command": "uvx",
            "args": [
                "fastmcp_agents",
                "config", "--bundled", "flow_github-triage",
                "run"
            ]
        }
    }
}
```

## Use in Open WebUI

Follow the instructions in [Open WebUI](../usage/web_ui.md) to run Open WebUI.

You can expose the server via mcpo:
```bash
uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled flow_github-triage run
``` 