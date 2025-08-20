#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform GitHub tasks.
"""

import os
from typing import ClassVar

from github.Issue import Issue
from pydantic import ConfigDict, Field
from pydantic_ai import RunContext
from pydantic_ai.agent import Agent
from pydantic_ai.tools import ToolDefinition

from fastmcp_agents.library.agents.github.agents.shared import (
    APPROACH,
    RESPONSE_FORMAT,
)
from fastmcp_agents.library.agents.github.dependencies.github import (
    GitHubClientDependency,
    GitHubRelatedItems,
    GitHubRelatedItemsDependency,
    ResearchGitHubIssueDependency,
    read_and_search_github_toolset,
)
from fastmcp_agents.library.mcp.github.github import github_search_syntax_help


class ResearchAgentDependency(ResearchGitHubIssueDependency, GitHubRelatedItemsDependency, GitHubClientDependency):
    """A dependency for the GitHub Research Agent."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)


class ResearchAgentInput(GitHubClientDependency):
    """An input for the Research Agent."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    issue_owner: str = Field(description="The owner of the issue to investigate.")
    issue_repo: str = Field(description="The repository of the issue to investigate.")
    issue_number: int = Field(description="The number of the issue to investigate.")

    def get_research_issue(self) -> Issue:
        """Get the issue to research."""
        return self.github_client.get_repo(full_name_or_id=f"{self.issue_owner}/{self.issue_repo}").get_issue(number=self.issue_number)

    def to_deps(self) -> ResearchAgentDependency:
        research_issue: Issue = self.get_research_issue()

        return ResearchAgentDependency(
            research_issue=research_issue,
            github_client=self.github_client,
        )

async def force_agent_tools(ctx: RunContext[ResearchAgentDependency], tool_defs: list[ToolDefinition]) -> list[ToolDefinition] | None:
    """Force the Agent to populate the checklist on the first step."""

    return tool_defs



async def report_completion(
    ctx: RunContext[GitHubRelatedItemsDependency],
) -> GitHubRelatedItems:
    """Report the related items that have been tagged during the investigation"""
    return ctx.deps.related_items


PERSONA = """
## Persona
You are a GitHub Research Agent. You are given a topic, issue, pull request, or other information and you
will use the provided tools to perform in-depth research across issues, pull requests and more to find items
relevant to the topic, issue, pull request, etc. Anything that might help the requester resolve their problem.
"""

RESEARCH_INSTRUCTIONS = """
## Research Instructions
You will perform multiple searches against the repository and organization. You are looking for issues, issue comments,
pull requests, code files, webpages and more that are relevant to the issue. Don't hesitate to perform multiple searches and
multiple types of searches at once.

As you locate relevant items, you will mark them as related to the issue using the related item tools available to you. You
will describe why you believe the item is related when calling the tool. When looking at Pull Requests, Issues and other items
you will pay careful attention to their current status (open, closed, merged, etc.), and for code and pull requests you will
double check that they do what they say they do.

When looking at Pull Requests, review the code changes and make sure they are what the pull request says they are.

Your goal is to find the most relevant items where you have high confidence that the items are related to the issue.

Examples of related items:
* An issue that is related to the issue because it is a duplicate of the issue or describes a subset or superset of the issue.
* A pull request that is related to the issue because it fixes the issue, attempted to fix the issue, or caused the issue. Or a
  pull request which fixed a very similar issue in the past.
* A code file that is related to the issue because it contains the code that fixes or causes the issue.
* A webpage that is related to the issue because it contains information relevant to the issue.

There is no time limit on your research. You can research for as long as you continue to identify relevant items
that are important to the requester.
"""

github_research_agent: Agent[ResearchAgentDependency, GitHubRelatedItems] = Agent[ResearchAgentDependency, GitHubRelatedItems](
    name="github-research-agent",
    model=os.getenv("MODEL_GITHUB_RESEARCH_AGENT") or os.getenv("MODEL"),
    instructions=[
        PERSONA,
        APPROACH,
        RESEARCH_INSTRUCTIONS,
        RESPONSE_FORMAT,
    ],
    end_strategy="exhaustive",
    toolsets=[read_and_search_github_toolset()],
    deps_type=ResearchAgentDependency,
    output_type=[report_completion],
)


@github_research_agent.instructions
async def github_query_tips(ctx: RunContext[ResearchAgentDependency]) -> str:
    """Tips for querying the GitHub API."""
    return github_search_syntax_help + (
        "It is wise to set the `per_page` argument to a smaller value like 10 or 20 for the first round of searching but"
        "feel free to increase it or view a second page of results if it is helpful!"
    )


@github_research_agent.instructions
async def research_github_issue_as_markdown(ctx: RunContext[ResearchAgentDependency]) -> str:
    """Provide the GitHub issue and comments to the Agent as markdown."""
    return ctx.deps.target_issue_as_markdown
