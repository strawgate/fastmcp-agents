# Open Webui

1. Run open-webui.  This is the best way:
```
docker pull ghcr.io/open-webui/open-webui:main
docker rm -f open-webui
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui -e WEBUI_AUTH=false --restart always ghcr.io/open-webui/open-webui:main
```
2. Run mcpo and your MCP Server to provide an OpenAPI interface for open webui to use: `uvx mcpo --port 8000 -- uvx fastmcp_agents config --bundled wrale_mcp-server-tree-sitter run`
3. Visit http://127.0.0.1:3000
4. Register your tool with open webui.  Click the account in the upper right and select `settings > tools > (+) add connection`.  Set the base url to http://localhost:8000 and click save.

For other bundled servers see [Bundled Servers](../../bundled/servers.md)!