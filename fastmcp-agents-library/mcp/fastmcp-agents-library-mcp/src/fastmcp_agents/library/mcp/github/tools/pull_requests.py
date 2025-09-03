from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig

from fastmcp_agents.library.mcp.github.tools.base import get_unique_objects, get_unique_scopes, get_unique_verbs

PULL_REQUEST_TOOLS: dict[str, ToolTransformConfig] = {
    "add_comment_to_pending_review": ToolTransformConfig(
        tags={"verb: add", "object: pull_request_review_comment", "scope: write"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "body": ArgTransformConfig(),
            "line": ArgTransformConfig(),
            "path": ArgTransformConfig(),
            "startLine": ArgTransformConfig(),
            "startSide": ArgTransformConfig(),
            "subjectType": ArgTransformConfig(),
        },
    ),
    "create_and_submit_pull_request_review": ToolTransformConfig(
        tags={"verb: create", "object: pull_request_review", "scope: write"},
        arguments={
            "commitID": ArgTransformConfig(),
            "event": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "body": ArgTransformConfig(),
        },
    ),
    "create_pending_pull_request_review": ToolTransformConfig(
        tags={"verb: create", "object: pull_request_review", "scope: write"},
        arguments={
            "commitID": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "create_pull_request": ToolTransformConfig(
        tags={"verb: create", "object: pull_request", "scope: write"},
        arguments={
            "base": ArgTransformConfig(),
            "body": ArgTransformConfig(),
            "draft": ArgTransformConfig(),
            "head": ArgTransformConfig(),
            "maintainer_can_modify": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "title": ArgTransformConfig(),
        },
    ),
    "delete_pending_pull_request_review": ToolTransformConfig(
        tags={"verb: delete", "object: pull_request_review", "scope: write"},
        arguments={
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "get_pull_request": ToolTransformConfig(
        tags={"verb: get", "object: pull_request", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "get_pull_request_comments": ToolTransformConfig(
        tags={"verb: get", "object: pull_request_comment", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "get_pull_request_diff": ToolTransformConfig(
        tags={"verb: get", "object: pull_request", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "get_pull_request_files": ToolTransformConfig(
        tags={"verb: get", "object: pull_request_file", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
        },
    ),
    "get_pull_request_reviews": ToolTransformConfig(
        tags={"verb: get", "object: pull_request_review", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "get_pull_request_status": ToolTransformConfig(
        tags={"verb: get", "object: pull_request", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "list_pull_requests": ToolTransformConfig(
        tags={"verb: list", "object: pull_request", "scope: read"},
        arguments={
            "base": ArgTransformConfig(),
            "direction": ArgTransformConfig(),
            "head": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "sort": ArgTransformConfig(),
            "state": ArgTransformConfig(),
        },
    ),
    "merge_pull_request": ToolTransformConfig(
        tags={"verb: merge", "object: pull_request", "scope: write"},
        arguments={
            "commit_message": ArgTransformConfig(),
            "commit_title": ArgTransformConfig(),
            "merge_method": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "request_copilot_review": ToolTransformConfig(
        tags={"verb: request", "object: pull_request_review", "scope: write"},
        arguments={
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "search_pull_requests": ToolTransformConfig(
        tags={"verb: search", "object: pull_request", "scope: read"},
        arguments={
            "order": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
            "query": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "sort": ArgTransformConfig(),
        },
    ),
    "submit_pending_pull_request_review": ToolTransformConfig(
        tags={"verb: submit", "object: pull_request_review", "scope: write"},
        arguments={
            "body": ArgTransformConfig(),
            "event": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
    "update_pull_request": ToolTransformConfig(
        tags={"verb: update", "object: pull_request", "scope: write"},
        arguments={
            "base": ArgTransformConfig(),
            "body": ArgTransformConfig(),
            "maintainer_can_modify": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "state": ArgTransformConfig(),
            "title": ArgTransformConfig(),
        },
    ),
    "update_pull_request_branch": ToolTransformConfig(
        tags={"verb: update", "object: pull_request", "scope: write"},
        arguments={
            "expectedHeadSha": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "pullNumber": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
        },
    ),
}

PULL_REQUEST_TOOL_SCOPES: set[str] = get_unique_scopes(tools=PULL_REQUEST_TOOLS)
PULL_REQUEST_TOOL_VERBS: set[str] = get_unique_verbs(tools=PULL_REQUEST_TOOLS)
PULL_REQUEST_TOOL_OBJECTS: set[str] = get_unique_objects(tools=PULL_REQUEST_TOOLS)
