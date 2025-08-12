import os
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Annotated, Literal

from git.repo import Repo
from github import Auth, Github
from github.Issue import Issue
from github.IssueComment import IssueComment
from pydantic import Field
from pydantic_ai import RunContext
from pydantic_ai.toolsets.function import FunctionToolset

from fastmcp_agents.library.agents.github.models import Checklist, GitHubIssue, GitHubRelatedIssue, IssueDrivenAgentInput, RelatedFile
from fastmcp_agents.library.agents.shared.models import Failure

if TYPE_CHECKING:
    from github.Repository import Repository


def get_github_client() -> Github:
    token: str | None = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")

    if not token:
        msg = "GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN must be set"
        raise ValueError(msg)

    return Github(auth=Auth.Token(token))


def get_issue(owner: str, repo: str, issue_number: int) -> Issue:
    github: Github = get_github_client()

    github_repo: Repository = github.get_repo(full_name_or_id=f"{owner}/{repo}")

    return github_repo.get_issue(number=issue_number)


def get_issue_comments(owner: str, repo: str, issue_number: int) -> list[IssueComment]:
    github: Github = get_github_client()

    github_repo: Repository = github.get_repo(full_name_or_id=f"{owner}/{repo}")

    return list[IssueComment](github_repo.get_issue(number=issue_number).get_comments())


def get_main_sha(owner: str, repo: str) -> str:
    github: Github = get_github_client()
    github_repo: Repository = github.get_repo(full_name_or_id=f"{owner}/{repo}")
    return github_repo.get_branch(branch=github_repo.default_branch).commit.sha


def get_blob_url(
    owner: str, repo: str, file_path: str, commit_sha: str | None = None, line_start: int | None = None, line_end: int | None = None
) -> str:
    if not commit_sha:
        commit_sha = get_main_sha(owner=owner, repo=repo)

    url: str = f"https://github.com/{owner}/{repo}/blob/{commit_sha}/{file_path}"

    if line_start:
        url += f"#L{line_start}"

    if line_end:
        url += f"-L{line_end}"

    return url


def create_initial_comment(owner: str, repo: str, issue_number: int, new_comment: str) -> int:
    """Create an initial comment on an issue."""
    repo_issue: Issue = get_issue(owner=owner, repo=repo, issue_number=issue_number)

    issue_comment: IssueComment = repo_issue.create_comment(body=new_comment)

    return issue_comment.id


def edit_issue_comment(owner: str, repo: str, issue_number: int, comment_id: int, new_comment: str) -> None:
    """Edit a comment on an issue."""
    repo_issue: Issue = get_issue(owner=owner, repo=repo, issue_number=issue_number)

    issue_comment: IssueComment = repo_issue.get_comment(id=comment_id)

    issue_comment.edit(body=new_comment)


def create_or_edit_issue_comment(owner: str, repo: str, issue_number: int, comment_id: int | None, new_comment: str) -> int:
    if comment_id:
        edit_issue_comment(owner=owner, repo=repo, issue_number=issue_number, comment_id=comment_id, new_comment=new_comment)
    else:
        comment_id = create_initial_comment(owner=owner, repo=repo, issue_number=issue_number, new_comment=new_comment)

    return comment_id


progress_update_toolset: FunctionToolset[IssueDrivenAgentInput] = FunctionToolset[IssueDrivenAgentInput]()


@progress_update_toolset.tool
def report_issue_encountered(run_context: RunContext[IssueDrivenAgentInput], issue: str) -> None:
    issue_driven_agent_input: IssueDrivenAgentInput = run_context.deps
    issue_driven_agent_input.add_issue_encountered(issue)


def generate_update_body(
    issue_driven_agent_input: IssueDrivenAgentInput, status: Literal["In Progress", "Completed", "Failed"], update_information: str
) -> str:
    """Generate the body of an update to the issue."""

    match status:
        case "In Progress":
            body = "## ⌛ Investigating issue"
        case "Completed":
            body = "## ✅ Investigation complete"
        case "Failed":
            body = "## ❌ Investigation failed"

    body += "\n\n### Latest Update\n\n" + update_information + "\n\n"

    body += issue_driven_agent_input.as_markdown()

    return body


def report_update(
    run_context: RunContext[IssueDrivenAgentInput], status: Literal["In Progress", "Completed", "Failed"], update_information: str
) -> str:
    """Report an update to the issue.

    Returns the body of the update.
    """

    issue_driven_agent_input: IssueDrivenAgentInput = run_context.deps
    github_issue: GitHubIssue = issue_driven_agent_input.investigate_issue

    update_body: str = generate_update_body(
        issue_driven_agent_input=issue_driven_agent_input, status=status, update_information=update_information
    )

    issue_driven_agent_input.comment_id = create_or_edit_issue_comment(
        owner=github_issue.owner,
        repo=github_issue.repo,
        issue_number=github_issue.issue_number,
        comment_id=issue_driven_agent_input.comment_id,
        new_comment=update_body,
    )

    return update_body


@progress_update_toolset.tool
def report_progress(
    run_context: RunContext[IssueDrivenAgentInput],
    current_task: Annotated[str, Field(description="The current task being worked on.")],
) -> str:
    """Report progress on the issue."""
    return report_update(run_context=run_context, status="In Progress", update_information=current_task)


def report_failure(run_context: RunContext[IssueDrivenAgentInput], failure: Failure) -> Failure:
    """Report a failure to the issue."""
    report_update(run_context=run_context, status="Failed", update_information=failure.reason)

    return failure


def report_completion(
    run_context: RunContext[IssueDrivenAgentInput],
    response: Annotated[
        str,
        Field(
            description=dedent(
                text="""
                The Markdown-formatted, detailed, response to the task. The Tasklist, related issues,
                and issues encountered will be automatically appended to the response. There is no limit
                to the length of the response.
                """
            )
        ),
    ],
) -> str:
    """Report the completion of the issue."""

    checklist_items = run_context.deps.checklist.get_incomplete_items()

    if checklist_items:
        msg = "Checklist items are not complete. Please complete or skip the remaining checklist items before reporting completion."
        raise ValueError(msg)

    return report_update(run_context=run_context, status="Completed", update_information=response)


@progress_update_toolset.tool
def add_to_checklist(
    run_context: RunContext[IssueDrivenAgentInput],
    items: Annotated[list[str], Field(description="The items to add to the checklist.")],
) -> Checklist:
    """Add items to the to-do checklist for this task. This checklist is used to track the items that need to be completed
    and is shared with the user who requested the assistance."""
    for item in items:
        run_context.deps.checklist.add_item(item)
    return run_context.deps.checklist


@progress_update_toolset.tool
def check_off_items(
    run_context: RunContext[IssueDrivenAgentInput],
    items: Annotated[list[str], Field(description="The items to check off the checklist.")],
) -> Checklist:
    """Check off items on the to-do checklist for this task. This checklist is used to track the items that need to be completed
    and is shared with the user who requested the assistance."""
    for item in items:
        run_context.deps.checklist.complete_item(item)
    return run_context.deps.checklist


@progress_update_toolset.tool
def skip_item(run_context: RunContext[IssueDrivenAgentInput], item: str) -> None:
    """Skip an item on the to-do checklist that is no longer relevant for this task."""
    run_context.deps.checklist.skip_item(item)


@progress_update_toolset.tool
def get_remaining_checklist_items(run_context: RunContext[IssueDrivenAgentInput]) -> list[str]:
    """Get the items remaining on the checklist."""
    return [item.description for item in run_context.deps.checklist.get_incomplete_items()]


@progress_update_toolset.tool
def get_formatted_checklist(run_context: RunContext[IssueDrivenAgentInput]) -> str:
    """Get the formatted checklist."""
    return run_context.deps.checklist.as_markdown()


@progress_update_toolset.tool
def add_related_issue(run_context: RunContext[IssueDrivenAgentInput], issue: GitHubRelatedIssue) -> None:
    """Add a related issue to the issue. These related issues are shared with the user who requested the assistance."""
    run_context.deps.add_related_issue(issue)


@progress_update_toolset.tool
def add_related_file(run_context: RunContext[IssueDrivenAgentInput], file: RelatedFile) -> None:
    """Add a related file to the issue. These related files are shared with the user who requested the assistance."""
    run_context.deps.add_related_file(file)


def git_diff(code_base: Path) -> str:
    """Get the diff of the code base."""
    repo = Repo(code_base)
    t = repo.head.commit.tree
    return repo.git.diff(t)
