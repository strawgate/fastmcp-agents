#!/usr/bin/env -S uv run fastmcp run

"""
This agent is used to perform GitHub tasks.
"""

import os
from textwrap import dedent
from typing import Annotated, ClassVar, Literal

from github.Issue import Issue
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import RunContext
from pydantic_ai.agent import Agent
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.tools import ToolDefinition

from fastmcp_agents.bridge.pydantic_ai.toolset import AbstractToolset
from fastmcp_agents.library.agents.evaluator.agents import FailedEvaluation, SuccessfulEvaluation, evaluate_performance
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
from fastmcp_agents.library.agents.search.toolsets import web_search_toolset_func, web_search_toolset_instructions
from fastmcp_agents.library.mcp.github.github import GITHUB_CODE_SEARCH_SYNTAX_HELP, GITHUB_SEARCH_SYNTAX_HELP


class ResearchAgentDependency(ResearchGitHubIssueDependency, GitHubRelatedItemsDependency, GitHubClientDependency, BaseModel):
    """A dependency for the GitHub Research Agent."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)


class ResearchAgentInput(GitHubClientDependency, BaseModel):
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


class SelfCheck(BaseModel):
    """A self-check to ensure you have completed the task correctly."""

    thorough: Annotated[
        Literal["very thorough", "thorough", "not thorough"],
        Field(description="The level of thoroughness you used in your work addressing the requested task."),
    ]

    searched_pull_requests: Annotated[
        bool,
        Field(
            description="Whether you have searched for related pull requests or you determined that searching for pull requests is not necessary."
        ),
    ]
    searched_issues: Annotated[
        bool,
        Field(description="Whether you have searched for related issues or you determined that searching for issues is not necessary."),
    ]
    searched_code: Annotated[
        bool, Field(description="Whether you have searched for related code or you determined that searching for code is not necessary.")
    ]
    searched_webpages: Annotated[
        bool,
        Field(description="Whether you have searched for related webpages or you determined that searching for webpages is not necessary."),
    ]

    double_checked: Annotated[bool, Field(description="Whether you are sure you're done researching!")]

    def thorough_enough(self) -> bool:
        """Whether the self-check has passed."""
        return self.thorough == "very thorough"

    def missed_items(self) -> tuple[list[str], list[str]]:
        missed_items: list[str] = []
        missed_item_instructions: list[str] = []
        if not self.searched_pull_requests:
            missed_items.append("pull requests")
            missed_item_instructions.append("You should use the search_pull_requests tool to search for related pull requests.")
        if not self.searched_issues:
            missed_item_instructions.append("You should use the search_issues tool to search for related issues.")
            missed_items.append("issues")
        if not self.searched_code:
            missed_item_instructions.append("You should use the search_code tool to search for related code.")
            missed_items.append("code")
        if not self.searched_webpages:
            missed_item_instructions.append("You should use the search_webpages tool to search for related webpages.")
            missed_items.append("webpages")

        if not self.double_checked:
            missed_items.append("double checked")

        if missed_items:
            return missed_items, missed_item_instructions

        return [], []


async def report_completion(
    ctx: RunContext[GitHubRelatedItemsDependency],
    self_check: SelfCheck,
) -> GitHubRelatedItems:
    """Report that you have completed the task. You should ensure you have been very thorough in your work and have
    completed all items in the self-check before attempting to report completion.

    You will be given a grade based on how your result fits with the tools you have called, their responses, and the original
    task description. If you have not completed the task or you have not actually performed the items you have indicated you
    performed, this will return a `ModelRetry` and you will receive a poor grade.
    """

    if not self_check.thorough_enough():
        raise ModelRetry(message="You must be very thorough in your work to complete the task.")


    missed_items, missed_item_instructions = self_check.missed_items()
    if missed_items:
        raise ModelRetry(
            message=(
                "You must indicate that you have considered each relevant type and either researched it or determined "
                f"that you have no further research to do for that type. Missed items: {missed_items}. "
                f" {missed_item_instructions}"
            )
        )

    performance: SuccessfulEvaluation | FailedEvaluation = await evaluate_performance(ctx)

    if isinstance(performance, FailedEvaluation):
        raise ModelRetry(message=performance.instructions)

    return ctx.deps.related_items


PERSONA = """
## Persona
You are a GitHub Research Agent, you are tasked with giving the requester a headstart with their investigation of an issue
or problem.
"""

RESEARCH_INSTRUCTIONS = """
## Research Instructions
You will perform multiple searches against the repository and organization. You are looking for issues, issue comments,
pull requests, code files, webpages and more that are relevant to the issue.

As you locate relevant items, you will first thoroughly investigate the items.

### Pull Requests

When looking at Pull Requests, you will pay careful attention to their current status (open, closed, merged, etc.). It is often the case
that the code in a Pull Request does not match the description of the Pull Request or that tasks marked as "completed" in the body of the
pull request are not actually completed. For this reason, if you believe a pull request is related to the current issue, you will call
`get_pull_request_diff` and `get_pull_request_files` and when you report the pull request as related you must note any identified
discrepancies between the actual code change and the description of the Pull Request.

### Issues

When looking at Issues, you will carefully consider the issue, as well as the comments on the issue. You will be sure to specifically note
the parts of the issue and comments that are relevant to the current issue.

You are looking for 1) Duplicate issues, 2) Issues that are closely related to the current issue, 3) Comments on previous issues that might
explain the behavior reported in the current issue.

### Code

When looking at code, you will carefully consider the code and the comments on the code. You will thoroughly review the related code to
understand whether the code is related to the issue and how the behavior you find in the code might explain the issue.

## Marking Related Items

Once you have completed investigating an item, you will mark the item as related to the issue using the related item tools available to
you. Your notes should include any noted discrepancies, etc about the related item.

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
    prepare_tools=force_agent_tools,
    output_type=[report_completion],
    output_retries=5,
)


@github_research_agent.instructions
async def github_query_tips(ctx: RunContext[ResearchAgentDependency]) -> str:
    """Tips for querying the GitHub API."""
    return dedent(
        f"""
        {GITHUB_SEARCH_SYNTAX_HELP}

        {GITHUB_CODE_SEARCH_SYNTAX_HELP}

        It is wise to set the `per_page` argument to a smaller value like 10 or 20 for the first round of searching but
        feel free to increase it or view a second page of results if it is helpful!
        """
    )


@github_research_agent.instructions
async def research_github_issue_as_markdown(ctx: RunContext[ResearchAgentDependency]) -> str:
    """Provide the GitHub issue and comments to the Agent as markdown."""
    issue_information: str = ctx.deps.target_issue_as_markdown

    dont_mark_issue_and_comments: str = dedent(f"""
        You do not need to mark the issue {ctx.deps.research_issue.number} or the comments under that issue
        as related, it's already marked.
    """)

    return issue_information + dont_mark_issue_and_comments


github_research_agent.toolset(web_search_toolset_func)

github_research_agent.instructions(web_search_toolset_instructions)


@github_research_agent.toolset(per_run_step=False)
async def related_items_toolset(ctx: RunContext[ResearchAgentDependency]) -> AbstractToolset[ResearchAgentDependency]:
    """A toolset for the related items."""
    return ctx.deps.related_items_toolset()
