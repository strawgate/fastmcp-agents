import os

from fastmcp.mcp_config import TransformingStdioMCPServer
from fastmcp.tools import Tool as FastMCPTool
from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig


def github_mcp(
    tools: dict[str, ToolTransformConfig] | None = None,
    include_tags: set[str] | None = None,
    exclude_tags: set[str] | None = None,
) -> TransformingStdioMCPServer:
    return TransformingStdioMCPServer(
        command="docker",
        args=[
            "run",
            "-i",
            "--rm",
            "-e",
            "GITHUB_PERSONAL_ACCESS_TOKEN",
            "ghcr.io/github/github-mcp-server",
        ],
        env=dict(os.environ.copy()),
        tools=tools or {},
        include_tags=include_tags,
        exclude_tags=exclude_tags,
    )


READ_ISSUE_TOOLS = {
    "get_issue",
    "get_issue_comments",
    "list_issues",
    "search_issues",
}

REPLY_ISSUE_TOOLS = {
    "add_issue_comment",
}

WRITE_ISSUE_TOOLS = {
    "add_issue_comment",
    "create_issue",
    "update_issue",
}

ISSUE_TOOLS = READ_ISSUE_TOOLS | WRITE_ISSUE_TOOLS

READ_PULL_REQUEST_TOOLS = {
    "get_pull_request",
    "get_pull_request_comments",
    "get_pull_request_diff",
    "get_pull_request_files",
    "get_pull_request_reviews",
    "get_pull_request_status",
    "list_pull_requests",
    "search_pull_requests",
}

WRITE_PULL_REQUEST_TOOLS = {
    "create_and_submit_pull_request_review",
    "create_pending_pull_request_review",
    "delete_pending_pull_request_review",
    "merge_pull_request",
    "request_copilot_review",
    "submit_pending_pull_request_review",
}

PULL_REQUEST_TOOLS = READ_PULL_REQUEST_TOOLS | WRITE_PULL_REQUEST_TOOLS

READ_DISCUSSION_TOOLS = {
    "get_discussion",
    "get_discussion_comments",
    "list_discussion_categories",
    "list_discussions",
}

WRITE_DISCUSSION_TOOLS: set[str] = set()

DISCUSSION_TOOLS = READ_DISCUSSION_TOOLS | WRITE_DISCUSSION_TOOLS

READ_REPOSITORY_TOOLS = {
    "get_commit",
    "get_file_contents",
    "get_tag",
    "list_branches",
    "list_commits",
    "list_tags",
}

WRITE_REPOSITORY_TOOLS = {
    "create_branch",
    "create_or_update_file",
    "delete_file",
    "fork_repository",
    "push_files",
}

REPOSITORY_TOOLS = READ_REPOSITORY_TOOLS | WRITE_REPOSITORY_TOOLS


def github_tools(
    issues: bool = False,
    pull_requests: bool = False,
    discussions: bool = False,
    repository: bool = False,
    read_tools: bool = True,
    write_tools: bool = True,
) -> set[str]:
    tools: set[str] = set()

    if read_tools:
        if issues:
            tools.update(READ_ISSUE_TOOLS)
        if pull_requests:
            tools.update(READ_PULL_REQUEST_TOOLS)
        if discussions:
            tools.update(READ_DISCUSSION_TOOLS)
        if repository:
            tools.update(READ_REPOSITORY_TOOLS)
    if write_tools:
        if issues:
            tools.update(WRITE_ISSUE_TOOLS)
        if pull_requests:
            tools.update(WRITE_PULL_REQUEST_TOOLS)
        if discussions:
            tools.update(WRITE_DISCUSSION_TOOLS)
        if repository:
            tools.update(WRITE_REPOSITORY_TOOLS)

    return tools


def restrict_github_mcp_server(
    github_mcp_server: TransformingStdioMCPServer | None = None,
    issues: bool = False,
    pull_requests: bool = False,
    discussions: bool = False,
    repository: bool = False,
    read_tools: bool = True,
    write_tools: bool = True,
) -> TransformingStdioMCPServer:
    if not github_mcp_server:
        github_mcp_server = github_mcp()

    tools = github_tools(
        issues=issues,
        pull_requests=pull_requests,
        discussions=discussions,
        repository=repository,
        read_tools=read_tools,
        write_tools=write_tools,
    )

    tool_transformations: dict[str, ToolTransformConfig] = dict.fromkeys(
        tools,
        ToolTransformConfig(
            tags={"restricted"},
        ),
    )

    github_mcp_server.tools = tool_transformations
    github_mcp_server.include_tags = {"restricted"}

    return github_mcp_server


def repo_restrict_github_mcp(
    github_mcp_server: TransformingStdioMCPServer | None = None,
    owner: str | None = None,
    repo: str | None = None,
    issues: bool = False,
    pull_requests: bool = False,
    discussions: bool = False,
    repository: bool = False,
    read_tools: bool = True,
    write_tools: bool = True,
) -> TransformingStdioMCPServer:
    """Restrict a GitHub MCP server to a specific repository."""

    if not github_mcp_server:
        github_mcp_server = github_mcp()

    arg_transforms: dict[str, ArgTransformConfig] = {}

    if owner is not None:
        arg_transforms["owner"] = ArgTransformConfig(default=owner, hide=True)
    if repo is not None:
        arg_transforms["repo"] = ArgTransformConfig(default=repo, hide=True)

    tools = github_tools(
        issues=issues,
        pull_requests=pull_requests,
        discussions=discussions,
        repository=repository,
        read_tools=read_tools,
        write_tools=write_tools,
    )

    github_mcp_server.tools = dict.fromkeys(
        tools,
        ToolTransformConfig(
            tags={"restricted"},
            arguments=arg_transforms,
        ),
    )

    github_mcp_server.include_tags = {"restricted"}

    return github_mcp_server


def github_search_syntax_tool() -> FastMCPTool:
    return FastMCPTool.from_function(
        fn=github_search_syntax,
    )


def github_search_syntax() -> str:
    """Returns a helpful syntax guide for searching GitHub issues and pull requests."""
    return github_search_syntax_help


github_search_syntax_help = """
# GitHub Issue and Pull Request Search Syntax Summary

*   **Case Insensitivity**: Search is not case sensitive.
*   **Multi-word Terms**: Use double quotes around multi-word search terms (e.g., `label:"help wanted"`).
*   **Exclusion**: Use a minus (`-`) symbol before a qualifier to exclude results (e.g., `-author:octocat`). This does not work for `no:` qualifiers.
*   **Boolean Operators**:
    *   `AND`: Returns results where both statements are true (e.g., `label:"question" AND assignee:octocat`). A space between statements is treated as `AND`.
    *   `OR`: Returns results where either statement is true (e.g., `assignee:octocat OR assignee:hubot`).
*   **Nesting Filters**: Use parentheses `()` to group qualifiers for more complex filters (up to five levels deep). Example: `(type:"Bug" AND assignee:octocat) OR (type:"Feature" AND assignee:hubot)`
*   **Date Formatting**: Dates follow ISO8601 standard: `YYYY-MM-DD`. Optional time: `THH:MM:SS+00:00`.
*   **Range Qualifiers**: Use `>`, `<`, `>=`, `<=`, `..` for numerical and date ranges (e.g., `comments:>100`, `created:<2011-01-01`, `comments:500..1000`).

## Key Qualifiers

### Type and State

*   `type:pr` or `is:pr`: Matches pull requests only.
*   `type:issue` or `is:issue`: Matches issues only.
*   `state:open` or `is:open`: Matches open issues/pull requests.
*   `state:closed` or `is:closed`: Matches closed issues/pull requests.
*   `is:queued`: Matches pull requests currently queued to merge.
*   `reason:completed`: Filters issues closed as "completed".
*   `reason:"not planned"`: Filters issues closed as "not planned".
*   `is:merged`: Matches merged pull requests.
*   `is:unmerged`: Matches pull requests that are open or closed without being merged.
*   `is:locked`: Matches issues/pull requests with a locked conversation.
*   `is:unlocked`: Matches issues/pull requests with an unlocked conversation.

### Content and Location

*   `in:title`: Searches only in the title.
*   `in:body`: Searches only in the body.
*   `in:comments`: Searches only in the comments.
*   `in:title,body`: Searches in title or body.
*   `user:_USERNAME_`: Searches in repositories owned by a specific user.
*   `org:_ORGNAME_`: Searches in repositories owned by a specific organization.
*   `repo:_USERNAME/REPOSITORY_`: Searches in a specific repository.
*   `is:public`: Matches issues/PRs in public repositories.
*   `is:private`: Matches issues/PRs in private repositories you can access.
*   `archived:true`: Matches issues/PRs in archived repositories.
*   `archived:false`: Matches issues/PRs in unarchived repositories.
*   `language:_LANGUAGE_`: Filters by the primary language of the repository (e.g., `language:ruby`).

### People and Involvement

*   `author:_USERNAME_`: Finds issues/PRs created by a user or integration account (e.g., `author:octocat`, `author:app/robot`).
*   `assignee:_USERNAME_`: Finds issues/PRs assigned to a user.
*   `assignee:*`: Finds issues/PRs with *any* assignee (within a single repository).
*   `mentions:_USERNAME_`: Finds issues/PRs that mention a user.
*   `commenter:_USERNAME_`: Finds issues/PRs with a comment from a user.
*   `involves:_USERNAME_`: Finds issues/PRs where a user is involved (author, assignee, mentioner, or commenter).
*   `team:_ORGNAME/TEAMNAME_`: Finds issues/PRs that mention a specific team.
*   `@me`: Can be used with `author`, `assignee`, `mentions`, `commenter`, `user-review-requested` to
            refer to the current user (e.g., `author:@me`).

### Labels, Milestones, and Projects

*   `label:"_LABEL_"`: Filters by a specific label.
    *   Logical OR for labels: `label:"bug","wip"`
    *   Logical AND for labels: `label:"bug" label:"wip"`
*   `milestone:"_MILESTONE_"`: Filters by a specific milestone.
*   `project:_PROJECT_NUMBER_`: Filters by a specific project number.

### Pull Request Specific

*   `linked:pr`: Filters issues linked to a pull request by a closing reference.
*   `linked:issue`: Filters pull requests linked to an issue that the PR may close.
*   `head:_HEAD_BRANCH_`: Filters by the head branch name.
*   `base:_BASE_BRANCH_`: Filters by the base branch name.
*   `status:pending`: Filters PRs with a pending commit status.
*   `status:success`: Filters PRs with a successful commit status.
*   `status:failure`: Filters PRs with a failed commit status.
*   `_SHA_`: Searches for PRs containing a commit SHA (at least 7 characters).
*   `draft:true`: Matches draft pull requests.
*   `draft:false`: Matches pull requests ready for review.
*   `review:none`: Matches PRs that haven't been reviewed.
*   `review:required`: Matches PRs that require a review.
*   `review:approved`: Matches PRs approved by a reviewer.
*   `review:changes_requested`: Matches PRs where changes were requested.
*   `reviewed-by:_USERNAME_`: Matches PRs reviewed by a specific person.
*   `review-requested:_USERNAME_`: Matches PRs where a specific person is requested for review.
*   `user-review-requested:@me`: Matches PRs you have directly been asked to review.
*   `team-review-requested:_TEAMNAME_`: Matches PRs with review requests from a specific team.

### Missing Metadata

*   `no:label`: Matches issues/PRs without any labels.
*   `no:milestone`: Matches issues/PRs not associated with a milestone.
*   `no:assignee`: Matches issues/PRs not associated with an assignee.
*   `no:project`: Matches issues/PRs not associated with a project.

### Numerical Filters

*   `comments:_n_`: Filters by number of comments (e.g., `comments:>100`, `comments:500..1000`).
*   `interactions:_n_`: Filters by number of reactions and comments (e.g., `interactions:>2000`).
*   `reactions:_n_`: Filters by number of reactions (e.g., `reactions:>1000`).

### Date Filters

*   `created:_YYYY-MM-DD_`: Filters by creation date.
*   `updated:_YYYY-MM-DD_`: Filters by last update date.
*   `closed:_YYYY-MM-DD_`: Filters by closed date.
*   `merged:_YYYY-MM-DD_`: Filters by merged date (for PRs).

## Example Queries

*   `is:issue is:open author:octocat label:"bug"`: Open bugs created by octocat.
*   `type:pr review:required language:javascript`: JavaScript pull requests requiring review.
*   `repo:octo-org/octo-project comments:>50 created:>=2023-01-01`: Issues/PRs in `octo-org/octo-project` with
        over 50 comments created since Jan 1, 2023.
*   `is:issue no:assignee no:milestone`: Issues with no assignee and no milestone.
*   `team:myorg/frontend-team is:open is:pr`: Open pull requests mentioning the `myorg/frontend-team`.
"""  # noqa: E501
