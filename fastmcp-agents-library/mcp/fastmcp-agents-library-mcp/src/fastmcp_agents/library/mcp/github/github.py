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


GET_ISSUE_TOOL = ToolTransformConfig(
    tags={"verb: get", "object: issue", "scope: read"},
    arguments={
        "owner": ArgTransformConfig(),
        "repo": ArgTransformConfig(),
        "issue_number": ArgTransformConfig(),
    },
)

GET_ISSUE_COMMENTS_TOOL = ToolTransformConfig(
    tags={"verb: get", "object: issue_comment", "scope: read"},
    arguments={
        "owner": ArgTransformConfig(),
        "repo": ArgTransformConfig(),
        "issue_number": ArgTransformConfig(),
        "page": ArgTransformConfig(),
        "per_page": ArgTransformConfig(),
    },
)

LIST_ISSUE_TYPES_TOOL = ToolTransformConfig(
    tags={"verb: list", "object: issue_type", "scope: read"},
    arguments={
        "owner": ArgTransformConfig(),
    },
)

LIST_ISSUES_TOOL = ToolTransformConfig(
    tags={"verb: list", "object: issue", "scope: read"},
    arguments={
        "owner": ArgTransformConfig(),
        "repo": ArgTransformConfig(),
        "after": ArgTransformConfig(),
        "direction": ArgTransformConfig(),
        "labels": ArgTransformConfig(),
        "orderBy": ArgTransformConfig(),
        "perPage": ArgTransformConfig(),
        "since": ArgTransformConfig(),
        "state": ArgTransformConfig(),
    },
)

SEARCH_ISSUES_TOOL = ToolTransformConfig(
    tags={"verb: search", "object: issue", "scope: read"},
    arguments={
        "owner": ArgTransformConfig(),
        "repo": ArgTransformConfig(),
        "order": ArgTransformConfig(),
        "page": ArgTransformConfig(),
        "perPage": ArgTransformConfig(),
        "query": ArgTransformConfig(),
        "sort": ArgTransformConfig(),
    },
)


READ_ISSUE_TOOLS: set[str] = {
    "get_issue",
    "get_issue_comments",
}

SEARCH_ISSUE_TOOLS = {
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

ISSUE_TOOLS = READ_ISSUE_TOOLS | WRITE_ISSUE_TOOLS | SEARCH_ISSUE_TOOLS

READ_PULL_REQUEST_TOOLS = {
    "get_pull_request",
    "get_pull_request_comments",
    "get_pull_request_diff",
    "get_pull_request_files",
    "get_pull_request_reviews",
    "get_pull_request_status",
}

SEARCH_PULL_REQUEST_TOOLS = {
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

PULL_REQUEST_TOOLS = READ_PULL_REQUEST_TOOLS | WRITE_PULL_REQUEST_TOOLS | SEARCH_PULL_REQUEST_TOOLS

READ_DISCUSSION_TOOLS = {
    "get_discussion",
    "get_discussion_comments",
}

SEARCH_DISCUSSION_TOOLS = {
    "list_discussions",
    "list_discussion_categories",
}

WRITE_DISCUSSION_TOOLS: set[str] = set()

DISCUSSION_TOOLS = READ_DISCUSSION_TOOLS | WRITE_DISCUSSION_TOOLS | SEARCH_DISCUSSION_TOOLS

READ_FILE_TOOLS = {
    "get_file_contents",
}

WRITE_FILE_TOOLS = {
    "create_or_update_file",
    "delete_file",
}

FILE_TOOLS = READ_FILE_TOOLS | WRITE_FILE_TOOLS


READ_REPOSITORY_TOOLS = {
    "get_commit",
    "get_tag",
    "list_branches",
    "list_commits",
    "list_tags",
}

WRITE_REPOSITORY_TOOLS = {
    "create_branch",
    "fork_repository",
    "push_files",
}

REPOSITORY_TOOLS = READ_REPOSITORY_TOOLS | WRITE_REPOSITORY_TOOLS


def file_tools(
    owner: str | None = None,
    repository: str | None = None,
    read_tools: bool = False,
    write_tools: bool = False,
) -> dict[str, ToolTransformConfig]:
    """Get the tools for a GitHub file."""

    def arg_transform() -> dict[str, ArgTransformConfig]:
        arg_transforms: dict[str, ArgTransformConfig] = {}

        if owner is not None:
            arg_transforms["owner"] = ArgTransformConfig(default=owner, hide=True)
        if repository is not None:
            arg_transforms["repository"] = ArgTransformConfig(default=repository, hide=True)

        return arg_transforms

    tools: set[str] = set()

    if read_tools:
        tools.update(READ_FILE_TOOLS)
    if write_tools:
        tools.update(WRITE_FILE_TOOLS)

    return {
        tool: ToolTransformConfig(
            tags={"allowed"},
            arguments=arg_transform(),
        )
        for tool in tools
    }


def issue_tools(
    owner: str | None = None,
    repository: str | None = None,
    read_tools: bool = False,
    write_tools: bool = False,
    search_tools: bool = False,
) -> dict[str, ToolTransformConfig]:
    """Get the tools for a GitHub issue."""

    def arg_transform() -> dict[str, ArgTransformConfig]:
        arg_transforms: dict[str, ArgTransformConfig] = {}

        if owner is not None:
            arg_transforms["owner"] = ArgTransformConfig(default=owner, hide=True)
        if repository is not None:
            arg_transforms["repository"] = ArgTransformConfig(default=repository, hide=True)

        return arg_transforms

    tools: set[str] = set()

    if read_tools:
        tools.update(READ_ISSUE_TOOLS)
    if write_tools:
        tools.update(WRITE_ISSUE_TOOLS)
    if search_tools:
        tools.update(SEARCH_ISSUE_TOOLS)

    return {
        tool: ToolTransformConfig(
            tags={"allowed"},
            arguments=arg_transform(),
        )
        for tool in tools
    }


def github_read_tools(
    issues: bool = False,
    pull_requests: bool = False,
    files: bool = False,
    discussions: bool = False,
    repository: bool = False,
) -> set[str]:
    tools: set[str] = set()

    if issues:
        tools.update(READ_ISSUE_TOOLS)
    if pull_requests:
        tools.update(READ_PULL_REQUEST_TOOLS)
    if discussions:
        tools.update(READ_DISCUSSION_TOOLS)
    if repository:
        tools.update(READ_REPOSITORY_TOOLS)
    if files:
        tools.update(READ_FILE_TOOLS)
    return tools


def github_write_tools(
    issues: bool = False,
    pull_requests: bool = False,
    discussions: bool = False,
    repository: bool = False,
) -> set[str]:
    tools: set[str] = set()

    if issues:
        tools.update(WRITE_ISSUE_TOOLS)
    if pull_requests:
        tools.update(WRITE_PULL_REQUEST_TOOLS)
    if discussions:
        tools.update(WRITE_DISCUSSION_TOOLS)
    if repository:
        tools.update(WRITE_REPOSITORY_TOOLS)

    return tools


def github_search_tools(
    issues: bool = False,
    pull_requests: bool = False,
    discussions: bool = False,
) -> set[str]:
    tools: set[str] = set()

    if issues:
        tools.update(SEARCH_ISSUE_TOOLS)
    if pull_requests:
        tools.update(SEARCH_PULL_REQUEST_TOOLS)
    if discussions:
        tools.update(SEARCH_DISCUSSION_TOOLS)

    return tools


def github_tools(
    issues: bool = False,
    pull_requests: bool = False,
    discussions: bool = False,
    repository: bool = False,
    read_tools: bool = True,
    write_tools: bool = True,
    search_tools: bool = True,
) -> set[str]:
    tools: set[str] = set()

    if read_tools:
        tools.update(github_read_tools(issues, pull_requests, discussions, repository))
    if write_tools:
        tools.update(github_write_tools(issues, pull_requests, discussions, repository))
    if search_tools:
        tools.update(github_search_tools(issues, pull_requests, discussions))

    return tools


def restrict_github_mcp_server(
    github_mcp_server: TransformingStdioMCPServer | None = None,
    issues: bool = False,
    pull_requests: bool = False,
    discussions: bool = False,
    repository: bool = False,
    read_tools: bool = True,
    write_tools: bool = True,
    search_tools: bool = True,
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
        search_tools=search_tools,
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
    search_tools: bool = True,
) -> TransformingStdioMCPServer:
    """Restrict a GitHub MCP server to a specific repository."""

    if not github_mcp_server:
        github_mcp_server = github_mcp()

    def arg_transform() -> dict[str, ArgTransformConfig]:
        arg_transforms: dict[str, ArgTransformConfig] = {}

        if owner is not None:
            arg_transforms["owner"] = ArgTransformConfig(default=owner, hide=True)
        if repo is not None:
            arg_transforms["repo"] = ArgTransformConfig(default=repo, hide=True)

        return arg_transforms

    tools = github_tools(
        issues=issues,
        pull_requests=pull_requests,
        discussions=discussions,
        repository=repository,
        read_tools=read_tools,
        write_tools=write_tools,
        search_tools=search_tools,
    )

    github_mcp_server.tools = {
        tool: ToolTransformConfig(
            tags={"restricted"},
            arguments=arg_transform(),
        )
        for tool in tools
    }

    github_mcp_server.include_tags = {"restricted"}

    return github_mcp_server


def github_search_syntax_tool() -> FastMCPTool:
    return FastMCPTool.from_function(
        fn=github_search_syntax,
    )


def github_search_syntax() -> str:
    """Returns a helpful syntax guide for searching GitHub issues and pull requests."""
    return GITHUB_SEARCH_SYNTAX_HELP


GITHUB_SEARCH_SYNTAX_HELP = """
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

By default, search terms are ANDed together, if you want to match any of the search terms, use the OR operator.

For example, if you search with `is:pr is:open tomato potato cucumber`, the only results will be pull requests that contain
all of the words `tomato`, `potato`, and `cucumber`. If you want to match any of the search terms, use the OR operator.
For example, if you search with `is:pr is:open tomato OR potato OR cucumber`, the results will be pull requests that contain
any of the words `tomato`, `potato`, or `cucumber`.

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

GITHUB_CODE_SEARCH_SYNTAX_HELP = """
# GitHub Code Search Syntax Summary

*   **Case Insensitivity**: Search is not case sensitive by default.
*   **Multi-word Terms**: Use double quotes around multi-word search terms (e.g., `"sparse index"`).
*   **Boolean Operators**:
    *   `AND`: Returns results where both statements are true (e.g., `sparse AND index`). A space between terms is treated as `AND`.
    *   `OR`: Returns results where either statement is true (e.g., `sparse OR index`).
    *   `NOT`: Excludes files from search results (e.g., `"fatal error" NOT path:__testing__`).
*   **Nesting Filters**: Use parentheses `()` to group qualifiers for more complex filters (e.g., `(language:ruby OR language:python) AND NOT path:"/tests/"`).
*   **Regular Expressions**: Surround regex patterns in slashes (e.g., `/sparse.*index/`).

By default, search terms are ANDed together. For example, `sparse index` will find files containing both terms.

## Key Qualifiers

### Repository and Organization

*   `repo:_OWNER/REPOSITORY_`: Search within a specific repository (e.g., `repo:github-linguist/linguist`).
*   `org:_ORGNAME_`: Search within an organization (e.g., `org:github`).
*   `user:_USERNAME_`: Search within a personal account (e.g., `user:octocat`).

### Language and Content

*   `language:_LANGUAGE_`: Filter by programming language (e.g., `language:ruby`, `language:cpp`).
*   `content:_TERM_`: Restrict search to file content only, not file paths.
*   `path:_PATTERN_`: Search within file paths using glob patterns or regex.

### Path Patterns

*   `path:*.txt`: Files with .txt extension.
*   `path:src/*.js`: JavaScript files in src directory.
*   `path:/src/*.js`: JavaScript files directly in src directory (anchored).
*   `path:/src/**/*.js`: JavaScript files in src and subdirectories.
*   `path:*.a?c`: Files matching pattern like file.aac or file.abc.
*   `path:"file?"`: Literal filename containing special characters.

### Symbol Search

*   `symbol:_SYMBOL_`: Search for function/class definitions (e.g., `language:go symbol:WithContext`).
*   **Supported Languages**: Bash, C, C#, C++, CodeQL, Elixir, Go, JSX, Java, JavaScript, Lua, PHP, Protocol Buffers, Python, R, Ruby, Rust, Scala, Starlark, Swift, TypeScript.

### Repository Properties

*   `is:archived`: Search in archived repositories.
*   `is:fork`: Search in forked repositories.
*   `is:vendored`: Search in vendored content.
*   `is:generated`: Search in generated content.

## Search Techniques

### Exact String Matching

*   `"sparse index"`: Search for exact phrase including whitespace.
*   `path:git language:"protocol buffers"`: Use quoted strings in qualifiers.

### Regular Expressions

*   `/sparse.*index/`: Basic regex pattern matching.
*   `/^App\\/src\\//`: Escaped forward slashes in regex.
*   `/(?-i)True/`: Case-sensitive regex search.
*   **Escape Sequences**: `\n` (newline), `\t` (tab)

### Boolean Logic

*   `sparse AND index`: Explicit AND operator.
*   `sparse OR index`: Either term.
*   `"fatal error" NOT path:__testing__`: Exclude specific paths.
*   `(language:ruby OR language:python) AND NOT path:"/tests/"`: Complex nested logic.

## Example Queries

*   `language:javascript path:src/*.js`: JavaScript files in src directory.
*   `repo:github-linguist/linguist language:ruby`: Ruby code in specific repository.
*   `symbol:WithContext language:go`: Go function definitions named WithContext.
*   `"error handling" NOT path:test/`: Error handling code excluding test files.
*   `path:/src/**/*.py language:python`: Python files in src and subdirectories.
*   `is:archived language:c`: C code in archived repositories.
"""  # noqa: E501
