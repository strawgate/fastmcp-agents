# MCP Inspector

To use FastMCP Agents with MCP Inspector, follow these steps:

1.  **Start the MCP Server:**
    Run your FastMCP Agents server, for example, using a bundled server like `wrale_mcp-server-tree-sitter`:
    ```bash
    uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter run
    ```
    This command starts an MCP server that exposes the `ask_tree_sitter` agent.

2.  **Open MCP Inspector:**
    Navigate to the MCP Inspector interface in your web browser:
    ```
    http://localhost:6274/#tools
    ```

3.  **Connect to your MCP Server:**
    In the MCP Inspector, click the `Connect` button to establish a connection with your running FastMCP Agents server.

4.  **List Available Tools:**
    Click `List Tools` to display all the tools and agents exposed by your connected server.

5.  **Select an Agent/Tool:**
    Click on the `ask_tree_sitter` agent (or any other tool you wish to interact with) from the list.

6.  **Interact with the Tool:**
    Use the instructions text area provided in the Inspector to send commands or queries to the selected agent/tool.

**Important Note on Timeout:**
When you set up the Inspector for the first time, the request timeout defaults to 10 seconds. For agents that might require more time to process complex tasks, ensure you modify this setting to 120 seconds or more under "Configuration" > "Request Timeout" in MCP Inspector.