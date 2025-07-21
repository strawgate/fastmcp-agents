from typing import Annotated, Literal

from fastmcp import Context
from fastmcp.tools import FunctionTool
from fastmcp.tools.tool import ToolResult
from fastmcp.tools.tool_transform import ArgTransform, TransformedTool

from fastmcp_agents.core.agents.base import FastMCPTool
from fastmcp_agents.core.utilities.mcp import get_text_from_tool_result

# async def get_issue(ctx: Context, owner: str, repo: str, issue_number: int) -> ToolResult:
#     github_issue: ToolResult = await ctx.fastmcp._call_tool(
#         "get_issue",
#         arguments={
#             "owner": owner,
#             "repo": repo,
#             "issue_number": issue_number,
#         },
#     )

#     return github_issue


# async def get_issue_comments(ctx: Context, owner: str, repo: str, issue_number: int) -> ToolResult:
#     github_issue_comments: ToolResult = await ctx.fastmcp._call_tool(
#         "get_issue_comments",
#         arguments={
#             "owner": owner,
#             "repo": repo,
#             "per_page": 100,
#             "issue_number": issue_number,
#         },
#     )

#     return github_issue_comments


# class RelatedKeywords(BaseModel):
#     keywords: list[str]


# class RelatedIssues(BaseModel):
#     issue_numbers: list[int]


# async def related_issues_completion(ctx: Context, owner: str, repo: str, background: str) -> list[ContentBlock]:
#     def provide_keywords(keywords: list[str]) -> RelatedKeywords:
#         return RelatedKeywords(keywords=keywords)

#     _, _, pending_tool_call = await ctx.completions.tool(
#         system_prompt="""Review the background information for the following GitHub issue and provide a list of important
#         keywords that can be used to search for related issues. Provide no more than 5 keywords.""",
#         messages=background,
#         tools=[FunctionTool.from_function(fn=provide_keywords)],
#     )

#     _, result = await pending_tool_call.run()

#     if isinstance(result, ToolError):
#         raise result

#     keywords: list[str] = result.structured_content.get("keywords", []) if result.structured_content else []

#     related_issues_search: ToolResult = await search_issues(ctx, owner, repo, keywords)

#     def provide_issue_numbers(issue_numbers: list[int]) -> RelatedIssues:
#         return RelatedIssues(issue_numbers=issue_numbers)

#     _, _, pending_tool_call = await ctx.completions.tool(
#         system_prompt="""
#         Review the background information for the following GitHub issue and the provided list of search results and provide a
#         list of likely related issue numbers from the search results.",
#         """,
#         messages=[
#             background,
#             str(related_issues_search.structured_content),
#         ],
#         tools=[FunctionTool.from_function(fn=provide_issue_numbers)],
#     )

#     _, result = await pending_tool_call.run()

#     if isinstance(result, ToolError):
#         raise result

#     issue_numbers: list[int] = result.structured_content.get("issue_numbers", []) if result.structured_content else []

#     related_issues: list[ToolResult] = [await get_issue(ctx, owner, repo, issue_number) for issue_number in issue_numbers]

#     issues: list[ContentBlock] = []

#     for related_issue in related_issues:
#         issues.extend(related_issue.content)

#     return issues


async def search_issues(
    ctx: Context,
    owner: str,
    repo: str,
    keywords: Annotated[list[str], "The keywords to search for. Maximum of 5 keywords."],
    state: Literal["all", "open", "closed"] = "all",
) -> ToolResult:
    """Search for issues by keyword in a GitHub repo. If more than 5 keywords are provided, only the first 5 will be used."""

    search_query_parts: list[str] = ["is:issue", f"repo:{owner}/{repo}"]

    if state == "open":
        search_query_parts.append("state:open")
    elif state == "closed":
        search_query_parts.append("state:closed")

    search_query_parts.append(" OR ".join(keywords[:5]))

    github_issues: ToolResult = await ctx.fastmcp._call_tool(
        "search_issues",
        arguments={
            "q": " ".join(search_query_parts),
        },
    )

    return github_issues


search_issues_tool = FunctionTool.from_function(fn=search_issues)


async def get_issue_background(
    tools: dict[str, FastMCPTool],
    owner: str,
    repo: str,
    issue_number: int,
) -> tuple[str, str]:
    get_issue_tool: FastMCPTool | None = tools.get("get_issue")

    if get_issue_tool is None:
        msg = "get_issue tool not found"
        raise ValueError(msg)

    get_issue_comments_tool: FastMCPTool | None = tools.get("get_issue_comments")

    if get_issue_comments_tool is None:
        msg = "get_issue_comments tool not found"
        raise ValueError(msg)

    issue = await get_issue_tool.run(arguments={"owner": owner, "repo": repo, "issue_number": issue_number})

    issue_content: str = get_text_from_tool_result(issue)

    comments = await get_issue_comments_tool.run(arguments={"owner": owner, "repo": repo, "issue_number": issue_number})

    comments_content: str = get_text_from_tool_result(comments)

    return issue_content, comments_content


def owner_repo_args_transform_factory(owner: str, repo: str) -> dict[str, ArgTransform]:
    return {
        "owner": ArgTransform(default=owner, hide=True),
        "repo": ArgTransform(default=repo, hide=True),
    }


async def restricted_get_issue_tool_factory(tools: dict[str, FastMCPTool], owner: str, repo: str) -> TransformedTool:
    if get_issue_tool := tools.get("get_issue"):
        return TransformedTool.from_tool(
            get_issue_tool,
            transform_args=owner_repo_args_transform_factory(owner, repo),
        )

    msg = "get_issue tool not found"
    raise ValueError(msg)


async def restricted_get_pull_request_tool_factory(tools: dict[str, FastMCPTool], owner: str, repo: str) -> TransformedTool:
    if get_pull_request_tool := tools.get("get_pull_request"):
        return TransformedTool.from_tool(
            get_pull_request_tool,
            transform_args=owner_repo_args_transform_factory(owner, repo),
        )

    msg = "get_pull_request tool not found"
    raise ValueError(msg)


async def restricted_search_issues_tool_factory(owner: str, repo: str) -> TransformedTool:
    return TransformedTool.from_tool(
        search_issues_tool,
        transform_args=owner_repo_args_transform_factory(owner, repo),
    )


def generate_background(issue_content: str, comments_content: str, extra: str | None = None) -> str:
    """Generate a background for an issue."""
    background: str = f"""
    An issue has been reported in the repo.

    ```markdown
    {issue_content}
    ```

    There may be some discussion in the issue comments.

    ```markdown
    {comments_content}
    ```
    """

    if extra:
        background += f"\n\n{extra}"

    return background
