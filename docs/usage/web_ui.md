# Open WebUI

To integrate FastMCP Agents with Open WebUI, follow these steps:

1.  **Run Open WebUI:**
    The recommended way to run Open WebUI is using Docker:
    ```bash
    docker pull ghcr.io/open-webui/open-webui:main
    docker rm -f open-webui
    docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui -e WEBUI_AUTH=false --restart always ghcr.io/open-webui/open-webui:main
    ```
    This command pulls the latest Open WebUI Docker image, removes any existing container with the same name, and then runs a new container, mapping port 3000 on your host to port 8080 in the container.

2.  **Run `mcpo` and your FastMCP Agents Server:**
    `mcpo` (MCP OpenAPI) is used to expose your FastMCP Agents server as an OpenAPI interface, which Open WebUI can consume. Replace `wrale_mcp-server-tree-sitter` with the bundled server you wish to use.
    ```bash
    uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter run
    ```
    This command starts `mcpo` on port 8000 and proxies requests to your FastMCP Agents server.

3.  **Access Open WebUI:**
    Open your web browser and navigate to:
    ```
    http://127.0.0.1:3000
    ```

4.  **Register your FastMCP Agents Server with Open WebUI:**
    In the Open WebUI interface:
    *   Click on your account icon in the upper right corner.
    *   Select `settings`.
    *   Navigate to `tools`.
    *   Click the `(+) add connection` button.
    *   Set the `base url` to `http://localhost:8000`.
    *   Click `save`.