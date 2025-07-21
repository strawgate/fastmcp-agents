"""
This agent is used to triage issues on a GitHub repository.
"""

from fastmcp_agents.core.models.server_builder import FastMCPAgents
from fastmcp_agents.library.agent.github.issue_triage import GithubIssueTriageAgent
from fastmcp_agents.library.agent.github.shared.mcp import github_mcp_server

mcp_servers = {
    "github": github_mcp_server,
}


server = FastMCPAgents(
    name="triage-github-issue",
    mcp=mcp_servers,
    agents=[GithubIssueTriageAgent()],
).to_server()


if __name__ == "__main__":
    server.run(transport="sse")
