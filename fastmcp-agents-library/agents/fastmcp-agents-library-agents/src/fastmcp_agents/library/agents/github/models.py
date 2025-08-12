from functools import cached_property
from pathlib import Path
from typing import Literal

from github.Issue import Issue
from github.IssueComment import IssueComment
from pydantic import AnyHttpUrl, BaseModel, Field, PrivateAttr


class ChecklistItem(BaseModel):
    description: str = Field(description="The description of the item to add to the checklist.")
    completed: bool = Field(description="Whether the item is completed. Default is False.")
    skipped: bool = Field(description="Whether the item is skipped. Default is False.")


class Checklist(BaseModel):
    tasks: list[ChecklistItem] = Field(default_factory=list, description="A list of items to add to the checklist.")

    def add_item(self, item: str) -> None:
        self.tasks.append(ChecklistItem(description=item, completed=False, skipped=False))

    def complete_item(self, item: str) -> None:
        for this_item in self.tasks:
            if this_item.description == item:
                this_item.completed = True
                return

        msg = f"Item {item} not found in checklist"
        raise ValueError(msg)

    def skip_item(self, item: str) -> None:
        for this_item in self.tasks:
            if this_item.description == item:
                this_item.completed = True
                this_item.skipped = True
                return

        msg = f"Item {item} not found in checklist"
        raise ValueError(msg)

    def get_items(self) -> list[ChecklistItem]:
        return self.tasks

    def get_incomplete_items(self) -> list[ChecklistItem]:
        return [item for item in self.tasks if not item.completed]

    def get_completed_items(self) -> list[ChecklistItem]:
        return [item for item in self.tasks if item.completed]

    def as_markdown(self) -> str:
        result: list[str] = []
        for item in self.tasks:
            if item.skipped:
                # strike through the text of the description if skipped
                result.append(f"- [ ] ~~{item.description}~~")
            else:
                result.append(f"- [{'x' if item.completed else ' '}] {item.description}")
        return "\n".join(result)

    def percent_complete(self) -> float:
        if not self.tasks:
            return 0.0
        return len(self.get_completed_items()) / len(self.tasks) * 100

    def percent_complete_str(self) -> str:
        open_items_count: int = len(self.get_incomplete_items())
        return f"{self.percent_complete():.0f}% complete ({open_items_count} tasks remain)"


class GitHubIssue(BaseModel):
    owner: str = Field(description="The owner of the repository.")
    repo: str = Field(description="The name of the repository.")
    issue_number: int = Field(description="The number of the issue.")

    def link(self) -> AnyHttpUrl:
        return AnyHttpUrl(url=f"https://github.com/{self.owner}/{self.repo}/issues/{self.issue_number}")

    def repository_url(self) -> AnyHttpUrl:
        return AnyHttpUrl(url=f"https://github.com/{self.owner}/{self.repo}")

    def repository_git_url(self) -> AnyHttpUrl:
        return AnyHttpUrl(url=f"https://github.com/{self.owner}/{self.repo}.git")

    @cached_property
    def issue(self) -> Issue:
        from fastmcp_agents.library.agents.github.tools import get_issue

        return get_issue(owner=self.owner, repo=self.repo, issue_number=self.issue_number)

    @property
    def title(self) -> str:
        return self.issue.title

    @property
    def body(self) -> str | None:
        return self.issue.body

    @property
    def comments(self) -> list[IssueComment]:
        return list[IssueComment](self.issue.get_comments())


class GitHubRelatedIssue(GitHubIssue):
    """A related issue to the current issue."""

    relation_confidence: Literal["high", "medium", "low"] = Field(
        description="The confidence in the relation between the related issue and the current issue."
    )
    relation_reason: str = Field(description="The reason you believe there is a relation between the related issue and the current issue.")

    def as_markdown_row(self) -> str:
        return f'| [{self.title}]({self.link()}) | [{self.relation_confidence}](## "{self.relation_reason}") |\n'


class RelatedFileChunk(BaseModel):
    """A chunk of a file in the repository."""

    line_start: int = Field(description="The line number of the start of the chunk in the file.")
    line_end: int = Field(description="The line number of the end of the chunk in the file.")


class RelatedFile(BaseModel):
    """A link to a line in a file in the repository."""

    owner: str = Field(description="The owner of the repository.")
    repo: str = Field(description="The name of the repository.")

    file_path: str = Field(description="The path to the file in the repository.")

    commit_sha: str | None = Field(
        default=None, description="The SHA of the commit this file is from. Leave blank if the file is from the main branch."
    )

    chunks: list[RelatedFileChunk] = Field(description="The chunks of the file that are related to the issue.")

    relation_confidence: Literal["high", "medium", "low"] = Field(
        description="The confidence in the relation between the related issue and the current issue."
    )
    relation_reason: str = Field(description="The reason you believe there is a relation between the related issue and the specified file.")

    def link(self, line_start: int | None = None, line_end: int | None = None) -> str:
        from fastmcp_agents.library.agents.github.tools import get_blob_url

        return get_blob_url(
            owner=self.owner, repo=self.repo, file_path=self.file_path, commit_sha=self.commit_sha, line_start=line_start, line_end=line_end
        )

    def as_markdown_row(self) -> str:
        # Turn the chunks into links that are clickable [L41-L45](https://github.com/owner/repo/blob/main/file.py#L41-L45)
        chunks_markdown: list[str] = []
        for chunk in self.chunks:
            chunk_link: str = self.link(line_start=chunk.line_start, line_end=chunk.line_end)
            chunk_text: str = f"L{chunk.line_start}-{chunk.line_end}" if chunk.line_start != chunk.line_end else f"L{chunk.line_start}"
            chunks_markdown.append(f"[{chunk_text}]({chunk_link})")

        related_chunks: str = ", ".join(chunks_markdown)
        return f'| [{self.file_path}]({self.link()}) | [{self.relation_confidence}](## "{self.relation_reason}") | {related_chunks} |'


class IssueDrivenAgentOptions(BaseModel):
    allowed_tools: list[str] | None = Field(default=None, description="The tools that the Agent is allowed to use.")
    disallowed_tools: list[str] | None = Field(default=None, description="The tools that the Agent is not allowed to use.")
    code_base: Path = Field(default_factory=Path.cwd, description="The code base to use for the Agent.")


class IssueDrivenAgentInput(BaseModel):
    investigate_issue: GitHubIssue = Field(description="The issue to investigate.")

    options: IssueDrivenAgentOptions = Field(default_factory=IssueDrivenAgentOptions, description="Options for the Agent.")

    _comment_id: int | None = PrivateAttr(default=None)

    _related_issues: list[GitHubRelatedIssue] = PrivateAttr(default_factory=list)

    _related_files: list[RelatedFile] = PrivateAttr(default_factory=list)

    _checklist: Checklist = PrivateAttr(default_factory=Checklist)

    _issues_encountered: list[str] = PrivateAttr(default_factory=list)

    @property
    def checklist(self) -> Checklist:
        return self._checklist

    @property
    def comment_id(self) -> int | None:
        return self._comment_id

    @comment_id.setter
    def comment_id(self, comment_id: int) -> None:
        self._comment_id = comment_id

    @property
    def issues_encountered(self) -> list[str]:
        return self._issues_encountered

    def add_issue_encountered(self, issue: str) -> None:
        self._issues_encountered.append(issue)

    @property
    def related_issues(self) -> list[GitHubRelatedIssue]:
        return self._related_issues

    def add_related_issue(self, issue: GitHubRelatedIssue) -> None:
        self._related_issues.append(issue)

    @property
    def related_files(self) -> list[RelatedFile]:
        return self._related_files

    def add_related_file(self, file: RelatedFile) -> None:
        self._related_files.append(file)

    def as_markdown(self) -> str:
        sections: list[str] = []

        if self.related_issues:
            # Create a markdown table of the related issues
            related_issues_markdown: str = "| Issue | Confidence |\n|-----------|------------|\n"
            related_issues_markdown += "\n".join([issue.as_markdown_row() for issue in self.related_issues])

            sections.append(f"## Related Issues\n\n{related_issues_markdown}")

        if self.related_files:
            # Create a markdown table of the related files
            related_files_markdown: str = "| File | Confidence | Sections |\n|-----------|------------|------------|\n"
            related_files_markdown += "\n".join([file.as_markdown_row() for file in self.related_files])

            sections.append(f"## Related Files\n\n{related_files_markdown}")

        if self.issues_encountered:
            sections.append(f"## Issues Encountered\n{self.issues_encountered}")

        if self.checklist.tasks:
            sections.append(f"## Checklist Followed ({self.checklist.percent_complete_str()}):\n{self.checklist.as_markdown()}")

        return "\n\n".join(sections)
