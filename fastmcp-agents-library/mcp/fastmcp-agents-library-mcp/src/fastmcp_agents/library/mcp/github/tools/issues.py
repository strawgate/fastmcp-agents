from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig

from fastmcp_agents.library.mcp.github.tools.base import get_unique_objects, get_unique_scopes, get_unique_verbs

ISSUE_TOOLS: dict[str, ToolTransformConfig] = {
    "add_issue_comment": ToolTransformConfig(
        tags={"verb: add", "object: issue_comment", "scope: write"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "issue_number": ArgTransformConfig(),
            "body": ArgTransformConfig(),
        },
    ),
    "add_sub_issue": ToolTransformConfig(
        tags={"verb: add", "object: issue", "scope: write"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "issue_number": ArgTransformConfig(),
            "replace_parent": ArgTransformConfig(),
            "subIssueId": ArgTransformConfig(),
            "body": ArgTransformConfig(),
        },
    ),
    "assign_copilot_to_issue": ToolTransformConfig(
        tags={"verb: assign", "object: issue", "scope: write"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "issueNumber": ArgTransformConfig(),
        },
    ),
    "create_issue": ToolTransformConfig(
        tags={"verb: create", "object: issue", "scope: write"},
        arguments={
            "assignees": ArgTransformConfig(),
            "body": ArgTransformConfig(),
            "labels": ArgTransformConfig(),
            "milestone": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "title": ArgTransformConfig(),
        },
    ),
    "get_issue": ToolTransformConfig(
        tags={"verb: get", "object: issue", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "issue_number": ArgTransformConfig(),
        },
    ),
    "get_issue_comments": ToolTransformConfig(
        tags={"verb: get", "object: issue_comment", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "issue_number": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
        },
    ),
    "list_issue_types": ToolTransformConfig(
        tags={"verb: list", "object: issue_type", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
        },
    ),
    "list_issues": ToolTransformConfig(
        tags={"verb: list", "object: issue", "scope: read"},
        arguments={
            "direction": ArgTransformConfig(),
            "labels": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "perPage": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "since": ArgTransformConfig(),
            "state": ArgTransformConfig(),
        },
    ),
    "list_sub_issues": ToolTransformConfig(
        tags={"verb: list", "object: issue", "scope: read"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "issue_number": ArgTransformConfig(),
            "page": ArgTransformConfig(),
            "per_page": ArgTransformConfig(),
        },
    ),
    "remove_sub_issue": ToolTransformConfig(
        tags={"verb: remove", "object: issue", "scope: write"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "issue_number": ArgTransformConfig(),
            "subIssueId": ArgTransformConfig(),
        },
    ),
    "reprioritize_sub_issue": ToolTransformConfig(
        tags={"verb: reprioritize", "object: issue", "scope: write"},
        arguments={
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "issue_number": ArgTransformConfig(),
            "subIssueId": ArgTransformConfig(),
            "afterId": ArgTransformConfig(),
            "beforeId": ArgTransformConfig(),
        },
    ),
    "search_issues": ToolTransformConfig(
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
    ),
    "update_issue": ToolTransformConfig(
        tags={"verb: update", "object: issue", "scope: write"},
        arguments={
            "assignees": ArgTransformConfig(),
            "body": ArgTransformConfig(),
            "issue_number": ArgTransformConfig(),
            "labels": ArgTransformConfig(),
            "milestone": ArgTransformConfig(),
            "owner": ArgTransformConfig(),
            "repo": ArgTransformConfig(),
            "state": ArgTransformConfig(),
            "title": ArgTransformConfig(),
        },
    ),
}

ISSUE_TOOL_SCOPES: set[str] = get_unique_scopes(tools=ISSUE_TOOLS)
ISSUE_TOOL_VERBS: set[str] = get_unique_verbs(tools=ISSUE_TOOLS)
ISSUE_TOOL_OBJECTS: set[str] = get_unique_objects(tools=ISSUE_TOOLS)
