from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig

from fastmcp_agents.library.mcp.github.tools.base import get_unique_objects, get_unique_scopes, get_unique_verbs

REPOSITORY_TOOLS: dict[str, ToolTransformConfig] = {
    "create_branch": ToolTransformConfig(
        tags={"verb: create", "object: repository_branch", "scope: write"},
        arguments={
            "branch": ArgTransformConfig(),
            "from_branch": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "create_or_update_file": ToolTransformConfig(
        tags={"verb: create", "object: repository_branch_file", "scope: write"},
        arguments={
            "branch": ArgTransformConfig(),
            "content": ArgTransformConfig(),
            "message": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "path": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "sha": ArgTransformConfig(),
        },
    ),
    "create_repository": ToolTransformConfig(
        tags={"verb: create", "object: repository", "scope: write"},
        arguments={
            "autoInit": ArgTransformConfig(),
            "description": ArgTransformConfig(),
            "name": ArgTransformConfig(),
            "private": ArgTransformConfig(),
        },
    ),
    "delete_file": ToolTransformConfig(
        tags={"verb: delete", "object: repository_branch_file", "scope: write"},
        arguments={
            "branch": ArgTransformConfig(),
            "path": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "fork_repository": ToolTransformConfig(
        tags={"verb: fork", "object: repository", "scope: write"},
        arguments={
            "organization": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "get_commit": ToolTransformConfig(
        tags={"verb: get", "object: repository_commit", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "sha": ArgTransformConfig(),
        },
    ),
    "get_file_contents": ToolTransformConfig(
        tags={"verb: get", "object: repository_branch_file", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "path": ArgTransformConfig(),
            "ref": ArgTransformConfig(
                description=(
                    "A Git ref in the form of `refs/tags/{tag}`, `refs/heads/{branch}` or `refs/pull/{pr_number}/head`. "
                    "If not provided, the default branch will be used. Do not provide a plain branch name or tag name."
                )
            ),
            "repo": ArgTransformConfig(),
            "sha": ArgTransformConfig(),
        },
    ),
    "get_latest_release": ToolTransformConfig(
        tags={"verb: get", "object: repository_release", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "get_tag": ToolTransformConfig(
        tags={"verb: get", "object: repository_tag", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "tag": ArgTransformConfig(),
        },
    ),
    "list_branches": ToolTransformConfig(
        tags={"verb: list", "object: repository_branch", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
        },
    ),
    "list_commits": ToolTransformConfig(
        tags={"verb: list", "object: repository_commit", "scope: read"},
        arguments={
            "author": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
            "sha": ArgTransformConfig(),
        },
    ),
    "list_files": ToolTransformConfig(
        tags={"verb: list", "object: repository_file", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
        },
    ),
    "list_releases": ToolTransformConfig(
        tags={"verb: list", "object: repository_release", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
        },
    ),
    "list_tags": ToolTransformConfig(
        tags={"verb: list", "object: repository_tag", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
        },
    ),
    "push_files": ToolTransformConfig(
        tags={"verb: push", "object: repository_branch_file", "scope: write"},
        arguments={
            "branch": ArgTransformConfig(),
            "files": ArgTransformConfig(),
            "message": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "search_code": ToolTransformConfig(
        tags={"verb: search", "object: repository_code", "scope: search"},
        arguments={
            "order": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
            "q": ArgTransformConfig(),
            "sort": ArgTransformConfig(),
        },
    ),
    "search_repositories": ToolTransformConfig(
        tags={"verb: search", "object: repository", "scope: search"},
        arguments={
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
            "query": ArgTransformConfig(),
        },
    ),
}

REPOSITORY_TOOL_SCOPES: set[str] = get_unique_scopes(tools=REPOSITORY_TOOLS)
REPOSITORY_TOOL_VERBS: set[str] = get_unique_verbs(tools=REPOSITORY_TOOLS)
REPOSITORY_TOOL_OBJECTS: set[str] = get_unique_objects(tools=REPOSITORY_TOOLS)
