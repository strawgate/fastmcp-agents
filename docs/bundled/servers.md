# Bundled MCP Servers

FastMCP-Agents comes bundled with several pre-configured MCP server wrappers. These bundled configurations demonstrate how to integrate third-party MCP servers and expose them with augmented agents and tools.

You can run these bundled servers using the `config --bundled` option with the FastMCP-Agents CLI.

| Server | How to Run |
|--------|------------|
| Git (from MCP) | `uvx fastmcp_agents config --bundled mcp_git run` |
| Git (from Cyanheads) | `uvx fastmcp_agents config --bundled cyanheads_git-mcp-server run` |
| Github | `uvx fastmcp_agents config --bundled github_github-mcp-server run` |
| Tree Sitter | `uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter run` |
| Evaluator Optimizer | `uvx fastmcp_agents config --bundled evaluator_optimizer run` |

## Available Bundled Servers

### Git (from MCP)

*   **Description:** An embedded Git Agent for performing Git operations. This configuration uses the Git MCP server from the main MCP repository.
*   **Agent Name:** `Git Agent`
*   **Agent Description:** Assists with performing Git operations as requested by the user.
*   **Enhancements:** Provides better descriptions and parameter names for the Git tools.
*   **How to Run:**
    ```bash
    uvx fastmcp_agents config --bundled mcp_git run
    ```

### Git (from Cyanheads)

*   **Description:** Another embedded Git Agent for performing Git operations. This configuration uses the Git MCP server from the Cyanheads repository.
*   **Agent Name:** `git_agent`
*   **Agent Description:** Assists with performing Git operations as requested by the user.
*   **Enhancements:** Includes a fix for the `git_clone` tool related to the `depth: 0` issue.
*   **How to Run:**
    ```bash
    uvx fastmcp_agents config --bundled cyanheads_git-mcp-server run
    ```

### Github

*   **Description:** An embedded Github Agent focused on triaging GitHub issues and pull requests.
*   **Agent Names:**
    *   `summarize_github_issue`: Assists with summarizing a GitHub issue and comments.
    *   `summarize_pull_request`: Request a report on a GitHub pull request.
*   **Enhancements:** Adds a tool (`search_issues_query_syntax`) for getting documentation on the GitHub issue search query syntax.
*   **How to Run:**
    ```bash
    uvx fastmcp_agents config --bundled github_github-mcp-server run
    ```

### Tree Sitter

*   **Description:** An embedded Tree Sitter Agent for code search and analysis.
*   **Agent Name:** `ask_tree_sitter`
*   **Agent Description:** Ask the tree-sitter agent to find items in the codebase. It can search for text, symbols, classes, functions, variables, and more.
*   **Enhancements:** Adds a tool (`list_query_templates_tool`) for getting available query templates. (Note: The YAML description mentioned GitHub query syntax, but the actual tool added is `list_query_templates_tool` based on the `wrale_mcp-server-tree-sitter.yml` content. I will update the description to match the tool).
*   **How to Run:**
    ```bash
    uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter run
    ```

### Evaluator Optimizer

*   **Description:** An MCP server that provides a tool for evaluating the result of a task based on predefined criteria.
*   **Agent Name:** `task_result_evaluator`
*   **Agent Description:** Evaluates the result of a task and provides feedback on the quality of the result.
*   **Enhancements:** Provides a structured evaluation result including a grade and feedback.
*   **How to Run:**
    ```bash
    uvx fastmcp_agents config --bundled evaluator_optimizer run
    ```

### Filesystem Operations

*   **Description:** Provides tools for performing filesystem read and write operations.
*   **Agent Names:**
    *   `request_filesystem_operations`: Assists with performing Filesystem read and write operations.
    *   `request_filesystem_search`: Assists with locating file names, paths, sizes, and other metadata.
*   **Enhancements:** Wraps the underlying filesystem tools.
*   **How to Run:**
    ```bash
    uvx fastmcp_agents config --bundled strawgate_filesystem-operations run
    ```

### MotherDuckDB

*   **Description:** An embedded agent for interacting with an in-memory DuckDB database.
*   **Agent Name:** `ask_duckdb`
*   **Agent Description:** Ask the duckdb agent to work with an in-memory database on your behalf.
*   **Enhancements:** Provides tools for getting tips on loading JSON and writing DuckDB queries.
*   **How to Run:**
    ```bash
    uvx fastmcp_agents config --bundled motherduckdb_mcp-server-motherduck run
