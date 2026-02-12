import asyncio

import asyncclick as click

from fastmcp_agents.library.agents.github.dependencies.result import AgentResult
from fastmcp_agents.library.agents.github.server import triage_github_issue


@click.group()
async def cli():
    pass


@cli.command()
@click.option("--issue-owner", type=str, required=True)
@click.option("--issue-repo", type=str, required=True)
@click.option("--issue-number", type=int, required=True)
@click.option("--instructions", type=str, required=False)
async def triage(issue_owner: str, issue_repo: str, issue_number: int, instructions: str | None):
    result: AgentResult = await triage_github_issue(
        issue_owner=issue_owner,
        issue_repo=issue_repo,
        issue_number=issue_number,
        instructions=instructions,
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(cli())
