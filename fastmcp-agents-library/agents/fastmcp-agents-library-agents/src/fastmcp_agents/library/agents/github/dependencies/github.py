import os
from collections.abc import Callable, Sequence
from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Literal, Self

from github import Auth, Github
from github.ContentFile import ContentFile
from github.GithubObject import GithubObject, NotSet
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.PullRequest import PullRequest
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.toolsets import FunctionToolset

from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPServerToolset
from fastmcp_agents.library.agents.shared.helpers.markdown import (
    MarkdownLink,
    MarkdownTable,
    MarkdownTableCell,
    MarkdownTableRow,
    MarkdownTooltip,
)
from fastmcp_agents.library.mcp.github import repo_restrict_github_mcp
from fastmcp_agents.library.mcp.github.mcp import restrict_github_mcp

if TYPE_CHECKING:
    from fastmcp.mcp_config import TransformingStdioMCPServer
    from github.Repository import Repository


def get_github_client() -> Github:
    token: str | None = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")

    if not token:
        msg = "GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN must be set"
        raise ValueError(msg)

    return Github(auth=Auth.Token(token))


def strip_github_objects(github_objects: Sequence[GithubObject]) -> list[dict[str, Any]]:
    """Strip a GitHub object."""
    return [strip_result(github_object.raw_data) for github_object in github_objects]


def strip_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Recursively remove all keys which end in _url from the dictionary."""
    return [strip_result(result) for result in results]


def strip_result(result: dict[str, Any]) -> dict[str, Any]:
    """Recursively remove all keys which end in _url from the dictionary."""
    for k, v in result.items():
        if isinstance(v, dict):
            result[k] = strip_result(result=v)  # pyright: ignore[reportUnknownArgumentType]
        elif isinstance(v, list):
            list_items: list[Any] = []
            for item in v:  # pyright: ignore[reportUnknownVariableType]
                if isinstance(item, dict):
                    list_items.append(strip_result(result=item))  # pyright: ignore[reportUnknownArgumentType]
                else:
                    list_items.append(item)

            result[k] = list_items
        elif k.endswith("_url"):
            del result[k]

    return result


class GitHubClientDependency(BaseModel):
    """A mixin for the GitHub client."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    github_client: Github = Field(default_factory=get_github_client, description="The GitHub client to use for the Agent.")


# class BroadSearchResult(BaseModel):
#     """A result from a broad search."""

#     issues: list[Issue] = Field(default_factory=list, description="The issues found in the search.")

#     code_files: list[ContentFileSearchResult] = Field(default_factory=list, description="The code files found in the search.")

#     commits: list[CommitSearchResult] = Field(default_factory=list, description="The commits found in the search.")

#     topics: list[Topic] = Field(default_factory=list, description="The topics found in the search.")


# class GitHubIssue(BaseModel):
#     """A GitHub issue."""

#     owner: str = Field(description="The owner of the issue.")
#     repo: str = Field(description="The repository of the issue.")
#     issue_number: int = Field(description="The number of the issue.")

    # def is_pull_request(self, client: Github) -> bool:
    #     """Check if the issue is a pull request."""
    #     return self.get_issue(client=client).pull_request is not None

    # def get_issue(self, client: Github) -> Issue:
    #     """Get the issue."""
    #     return client.get_repo(full_name_or_id=f"{self.owner}/{self.repo}").get_issue(number=self.issue_number)

    # def get_comments(self, client: Github) -> list[IssueComment]:
    #     """Get the comments."""
    #     return list(client.get_repo(full_name_or_id=f"{self.owner}/{self.repo}").get_issue(number=self.issue_number).get_comments())

    # def get_comment(self, client: Github, comment_id: int) -> IssueComment:
    #     """Get the comment."""
    #     return client.get_repo(full_name_or_id=f"{self.owner}/{self.repo}").get_issue(number=self.issue_number).get_comment(id=comment_id)

    # def new_comment(self, client: Github, comment: str) -> IssueComment:
    #     """Create a new comment."""
    #     return client.get_repo(full_name_or_id=f"{self.owner}/{self.repo}").get_issue(number=self.issue_number).create_comment(body=comment)

    # def edit_comment(self, client: Github, comment_id: int, body: str) -> IssueComment:
    #     """Edit a comment."""
    #     comment: IssueComment = (
    #         client.get_repo(full_name_or_id=f"{self.owner}/{self.repo}").get_issue(number=self.issue_number).get_comment(id=comment_id)
    #     )
    #     comment.edit(body=body)
    #     return comment

    # def as_markdown(self, client: Github) -> str:
    #     github_issue: Issue = self.get_issue(client=client)

    #     owner_repo_number: str = f"{github_issue.repository.owner.login}/{github_issue.repository.name}#{github_issue.number}"

    #     type_str: str = "pull request" if github_issue.pull_request else "issue"

    #     github_issue_comments: list[IssueComment] = self.get_comments(client=client)
    #     formatted_issue_comments: str = "\n\n".join(
    #         [
    #             f"**{comment.user.role_name} {comment.user.login} at {comment.created_at.strftime('%Y-%m-%d %H:%M:%S')}**\n{comment.body}"
    #             for comment in github_issue_comments
    #         ]
    #     )

    #     return (
    #         f"The {type_str} for this task is: {owner_repo_number}\n"
    #         f"The {type_str} body is:\n```{github_issue.body}```\n"
    #         f"The {type_str} comments are:\n```{formatted_issue_comments}```"
    #     )


class ResearchGitHubIssueDependency(GitHubClientDependency):
    """A dependency for the GitHub Research Agent."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    research_issue: Issue = Field(description="The issue to research.")

    @classmethod
    def from_issue(cls, owner: str, repo: str, issue_number: int) -> Self:
        return cls(research_issue=cls.github_client.get_repo(full_name_or_id=f"{owner}/{repo}").get_issue(number=issue_number))

    @cached_property
    def pull_request_branch(self) -> str | None:
        """The branch to source the code from."""

        if self.research_issue.pull_request:
            return f"pull/{self.research_issue.number}/head"

        return None

    @cached_property
    def target_issue_comments(self) -> list[IssueComment]:
        """The comments on the target issue."""
        return list(self.research_issue.get_comments())

    def new_comment(self, comment: str) -> IssueComment:
        """Create a new comment."""
        return self.research_issue.create_comment(body=comment)

    def edit_comment(self, comment_id: int, body: str) -> IssueComment:
        """Edit a comment."""
        comment: IssueComment = self.research_issue.get_comment(id=comment_id)
        comment.edit(body=body)
        return comment

    @cached_property
    def target_issue_as_markdown(self) -> str:
        owner_repo_number: str = (
            f"{self.research_issue.repository.owner.login}/{self.research_issue.repository.name}#{self.research_issue.number}"
        )

        type_str: str = "pull request" if self.research_issue.pull_request else "issue"

        github_issue_comments: list[IssueComment] = self.target_issue_comments
        formatted_issue_comments: str = "\n\n".join(
            [
                f"**{comment.user.role_name} {comment.user.login} at {comment.created_at.strftime('%Y-%m-%d %H:%M:%S')}**\n{comment.body}"
                for comment in github_issue_comments
            ]
        )

        return (
            f"The {type_str} for this task is: {owner_repo_number}\n"
            f"The {type_str} body is:\n```{self.research_issue.body}```\n"
            f"The {type_str} comments are:\n```{formatted_issue_comments}```"
        )


class GitHubRelatedItemMixin(BaseModel):
    """A mixin for related items."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    relation_confidence: Literal["High", "Medium", "Low"] = Field(
        description="The confidence in the relation between the related issue and the current issue."
    )

    relation_reason: str = Field(
        description=(
            "The reason you believe there is a relation between the related issue and the current issue. "
            "Specifically outlining the reason you chose the confidence level and not something lower or higher."
        )
    )

    def relation_as_markdown_tooltip(self) -> MarkdownTooltip:
        return MarkdownTooltip(text=self.relation_confidence, tip=self.relation_reason)

    @classmethod
    def markdown_headers(cls) -> list[str]: ...

    def as_markdown(self) -> MarkdownTableRow: ...

    @classmethod
    def as_markdown_table(cls, items: list[Self]) -> MarkdownTable:
        return MarkdownTable(headers=cls.markdown_headers(), rows=[item.as_markdown() for item in items])


class RelatedWebpage(GitHubRelatedItemMixin):
    """A related webpage to the current issue."""

    name: str = Field(description="The name of the webpage.")

    url: str = Field(description="The URL of the webpage.")

    content: str | None = Field(
        default=None, description="The relevant content from the webpage. Enough to prevent having to go to the webpage."
    )

    def as_markdown(self) -> MarkdownTableRow:
        return MarkdownTableRow(
            cells=[
                MarkdownTableCell(text=self.name),
                MarkdownTableCell(text=self.url),
                MarkdownTableCell(text=self.relation_as_markdown_tooltip().render()),
            ]
        )

    @classmethod
    def markdown_headers(cls) -> list[str]:
        return ["Name", "URL", "Confidence"]


class RelatedIssue(GitHubRelatedItemMixin):
    """A related issue to the current issue."""

    issue: Issue = Field(description="The issue that is related to the current issue.")

    @classmethod
    def markdown_headers(cls) -> list[str]:
        return ["Issue", "Title", "Confidence"]

    def as_markdown(self) -> MarkdownTableRow:
        issue_link: str = f"{self.issue.repository.owner.login}/{self.issue.repository.name}#{self.issue.number}"

        markdown_link: MarkdownLink = MarkdownLink(text=issue_link, url=self.issue.html_url)
        return MarkdownTableRow(
            cells=[
                MarkdownTableCell(text=markdown_link.render()),
                MarkdownTableCell(text=self.issue.title),
                MarkdownTableCell(text=self.relation_as_markdown_tooltip().render()),
            ]
        )

    @field_serializer("issue")
    def serialize_issue(self, issue: Issue) -> dict[str, Any]:
        return issue.raw_data


class RelatedIssueComment(GitHubRelatedItemMixin):
    """A related issue comment to the current issue."""

    comment: IssueComment = Field(description="The comment that is related to the current issue.")

    context: str = Field(description="The relevant context from the comment.")

    @classmethod
    def markdown_headers(cls) -> list[str]:
        return ["Comment", "Context", "Confidence"]

    def as_markdown(self) -> MarkdownTableRow:
        markdown_link: MarkdownLink = MarkdownLink(text=self.comment.user.login, url=self.comment.html_url)
        return MarkdownTableRow(
            cells=[
                MarkdownTableCell(text=markdown_link.render()),
                MarkdownTableCell(text=self.context),
                MarkdownTableCell(text=self.relation_as_markdown_tooltip().render()),
            ]
        )

    @field_serializer("comment")
    def serialize_comment(self, comment: IssueComment) -> dict[str, Any]:
        return comment.raw_data


class RelatedPullRequest(GitHubRelatedItemMixin):
    """A related pull request to the current issue."""

    pull_request: PullRequest = Field(description="The pull request that is related to the current issue.")

    def as_issue(self) -> Issue:
        return self.pull_request.as_issue()

    @classmethod
    def markdown_headers(cls) -> list[str]:
        return ["Pull Request", "Title", "Confidence"]

    def as_markdown(self) -> MarkdownTableRow:
        as_issue: Issue = self.as_issue()
        markdown_link: MarkdownLink = MarkdownLink(text=as_issue.title, url=self.pull_request.html_url)
        return MarkdownTableRow(
            cells=[
                MarkdownTableCell(text=markdown_link.render()),
                MarkdownTableCell(text=as_issue.title),
                MarkdownTableCell(text=self.relation_as_markdown_tooltip().render()),
            ]
        )

    @field_serializer("pull_request")
    def serialize_pull_request(self, pull_request: PullRequest) -> dict[str, Any]:
        return pull_request.raw_data


class FileLineRange(BaseModel):
    """A range of line numbers in a file."""

    line_start: int = Field(description="The line number of the start of the range.")
    line_end: int | None = Field(default=None, description="The line number of the end of the range.")

    def to_line_range_link_str(self) -> str:
        return f"L{self.line_start}"

    def to_line_range_str(self) -> str:
        if self.line_start and not self.line_end:
            return f"{self.line_start}"

        return f"{self.line_start}-{self.line_end}"


class RelatedFile(GitHubRelatedItemMixin):
    """A related file to the current issue."""

    file: ContentFile = Field(description="The file that is related to the current issue.")

    line_numbers: list[FileLineRange] | None = Field(
        default=None, description="The line numbers of the file that are related to the current issue."
    )

    @classmethod
    def markdown_headers(cls) -> list[str]:
        return ["File", "Confidence", "Sections"]

    def as_markdown(self) -> MarkdownTableRow:
        markdown_link: MarkdownLink = MarkdownLink(text=self.file.name, url=self.file.html_url)
        line_range_links: list[str] = []
        for line_number in self.line_numbers or []:
            file_link: str = self.file.html_url + "#" + line_number.to_line_range_link_str()
            line_range_links.append(MarkdownLink(text=line_number.to_line_range_str(), url=file_link).render())

        return MarkdownTableRow(
            cells=[
                MarkdownTableCell(text=markdown_link.render()),
                MarkdownTableCell(text=self.relation_as_markdown_tooltip().render()),
                MarkdownTableCell(text=", ".join(line_range_links)),
            ]
        )

    @field_serializer("file")
    def serialize_file(self, file: ContentFile) -> dict[str, Any]:
        return file.raw_data


class GitHubRelatedItems(BaseModel):
    issues: list[RelatedIssue] = Field(default_factory=list, description="The issues that are related to the current issue.")

    issue_comments: list[RelatedIssueComment] = Field(
        default_factory=list, description="The issue comments that are related to the current issue."
    )

    pull_requests: list[RelatedPullRequest] = Field(
        default_factory=list, description="The pull requests that are related to the current issue."
    )

    files: list[RelatedFile] = Field(default_factory=list, description="The files that are related to the current issue.")

    webpages: list[RelatedWebpage] = Field(default_factory=list, description="The webpages that are related to the current issue.")

    def get(self) -> Self:
        """Get all related items."""
        return self

    def add_issue(self, issue: RelatedIssue) -> None:
        self.issues.append(issue)

    def add_issue_comment(self, issue_comment: RelatedIssueComment) -> None:
        self.issue_comments.append(issue_comment)

    def get_issue(self, owner: str, repo: str, issue_number: int) -> RelatedIssue | None:
        for related_issue in self.issues:
            if (
                related_issue.issue.repository.owner.login == owner
                and related_issue.issue.repository.name == repo
                and related_issue.issue.number == issue_number
            ):
                return related_issue

        return None

    def add_pull_request(self, pull_request: RelatedPullRequest) -> None:
        self.pull_requests.append(pull_request)

    def get_pull_request(self, owner: str, repo: str, pull_request_number: int) -> RelatedPullRequest | None:
        for related_pull_request in self.pull_requests:
            as_issue: Issue = related_pull_request.as_issue()
            if as_issue.repository.owner.login == owner and as_issue.repository.name == repo and as_issue.number == pull_request_number:
                return related_pull_request

        return None

    def add_file(self, file: RelatedFile) -> None:
        if existing_file := self.get_file(
            owner=file.file.repository.owner.login,
            repo=file.file.repository.name,
            branch=file.file.repository.default_branch,
            file_path=file.file.path,
        ):
            if file.line_numbers and existing_file.line_numbers:
                existing_file.line_numbers.extend(file.line_numbers)
            elif file.line_numbers:
                existing_file.line_numbers = file.line_numbers

            return

        self.files.append(file)

    def get_file(self, owner: str, repo: str, branch: str, file_path: str) -> RelatedFile | None:
        for related_file in self.files:
            if all(
                [
                    related_file.file.repository.owner.login == owner,
                    related_file.file.repository.name == repo,
                    related_file.file.repository.default_branch == branch,
                    related_file.file.path == file_path,
                ]
            ):
                return related_file

        return None

    def add_webpage(self, webpage: RelatedWebpage) -> None:
        self.webpages.append(webpage)

    def get_webpage(self, url: str) -> RelatedWebpage | None:
        for related_webpage in self.webpages:
            if related_webpage.url == url:
                return related_webpage

        return None

    @property
    def issues_as_markdown_table(self) -> MarkdownTable | None:
        if not self.issues:
            return None

        return RelatedIssue.as_markdown_table(items=self.issues)

    @property
    def issue_comments_as_markdown_table(self) -> MarkdownTable | None:
        if not self.issue_comments:
            return None

        return RelatedIssueComment.as_markdown_table(items=self.issue_comments)

    @property
    def pull_requests_as_markdown_table(self) -> MarkdownTable | None:
        if not self.pull_requests:
            return None

        return RelatedPullRequest.as_markdown_table(items=self.pull_requests)

    @property
    def files_as_markdown_table(self) -> MarkdownTable | None:
        if not self.files:
            return None

        return RelatedFile.as_markdown_table(items=self.files)

    @property
    def webpages_as_markdown_table(self) -> MarkdownTable | None:
        if not self.webpages:
            return None

        return RelatedWebpage.as_markdown_table(items=self.webpages)


class GitHubRelatedItemsDependency(GitHubClientDependency):
    """A dependency for tracking related GitHub items."""

    research_issue: Issue = Field(description="The issue to research.")

    related_items: GitHubRelatedItems = Field(default_factory=GitHubRelatedItems, description="The related items to track.")

    on_update: Callable[[GitHubRelatedItemMixin], None] = Field(
        default=lambda _: None, description="A callback to call when a related item is added."
    )

    def related_items_toolset(self) -> FunctionToolset[Any]:
        """Convert the bridge to a toolset."""
        toolset: FunctionToolset[Any] = FunctionToolset[Any](max_retries=3)

        toolset.add_function(func=self.add_related_issue, name="add_related_github_issue")
        toolset.add_function(func=self.add_related_issue_comment, name="add_related_github_issue_comment")
        toolset.add_function(func=self.add_related_pull_request, name="add_related_github_pull_request")
        toolset.add_function(func=self.add_related_file, name="add_related_repository_file")
        toolset.add_function(func=self.add_related_file_lines, name="add_related_repository_file_lines")
        toolset.add_function(func=self.add_related_webpage, name="add_related_web_page")
        toolset.add_function(func=self.related_items.get, name="get_all_related_items")

        return toolset

    def on_related_item_added(self, related_item: GitHubRelatedItemMixin) -> None:
        """Call the on_update callback."""

    # def _to_qualifiers(self, owner: str, repo: str | None, keywords: set[str]) -> dict[str, Any]:
    #     qualifiers: dict[str, Any] = {}
    #     if repo:
    #         qualifiers["repo"] = repo
    #     qualifiers["owner"] = owner
    #     qualifiers["q"] = " ".join(list[str](keywords))
    #     return qualifiers

    # def search_issues(self, owner: str, keywords: set[str], repo: str | None = None) -> list[dict[str, Any]]:
    #     """Search for issues in a repository."""
    #     qualifiers: dict[str, Any] = self._to_qualifiers(owner=owner, repo=repo, keywords=keywords)

    #     return strip_github_objects(github_objects=list(self.github_client.search_issues(**qualifiers)))

    # def search_code(self, owner: str, keywords: set[str], repo: str | None = None) -> list[dict[str, Any]]:
    #     """Search for code in a repository."""
    #     qualifiers: dict[str, Any] = self._to_qualifiers(owner=owner, repo=repo, keywords=keywords)
    #     return strip_github_objects(github_objects=list(self.github_client.search_code(**qualifiers)))

    # def search_commits(self, owner: str, keywords: set[str], repo: str | None = None) -> list[dict[str, Any]]:
    #     """Search for commits in a repository."""
    #     qualifiers: dict[str, Any] = self._to_qualifiers(owner=owner, repo=repo, keywords=keywords)
    #     return strip_github_objects(github_objects=list(self.github_client.search_commits(**qualifiers)))

    # def search_topics(self, owner: str, keywords: set[str], repo: str | None = None) -> list[dict[str, Any]]:
    #     """Search for topics in a repository."""
    #     qualifiers: dict[str, Any] = self._to_qualifiers(owner=owner, repo=repo, keywords=keywords)
    #     return strip_github_objects(github_objects=list(self.github_client.search_topics(**qualifiers)))

    # def search(self, owner: str, keywords: set[str]) -> dict[str, list[dict[str, Any]]]:
    #     """Search for issues, code, commits, topics, and repositories."""

    #     return {
    #         "issues": self.search_issues(owner=owner, keywords=keywords),
    #         "code": self.search_code(owner=owner, keywords=keywords),
    #         "commits": self.search_commits(owner=owner, keywords=keywords),
    #         "topics": self.search_topics(owner=owner, keywords=keywords),
    #     }

    def _matches_research_issue(self, owner: str, repo: str, issue_number: int) -> bool:
        return all(
            [
                self.research_issue.repository.owner.login == owner,
                self.research_issue.repository.name == repo,
                self.research_issue.number == issue_number,
            ]
        )

    def add_related_issue(
        self, owner: str, repo: str, issue_number: int, relation_confidence: Literal["High", "Medium", "Low"], relation_reason: str
    ) -> None:
        """Track a GitHub Issue as a related item for the current task."""
        if self._matches_research_issue(owner=owner, repo=repo, issue_number=issue_number):
            return

        try:
            repository: Repository = self.github_client.get_repo(full_name_or_id=f"{owner}/{repo}")

            issue: Issue = repository.get_issue(number=issue_number)
        except Exception as e:
            raise ModelRetry(message=f"Error getting issue {owner}/{repo}#{issue_number}: {e}") from e

        related_issue: RelatedIssue = RelatedIssue(issue=issue, relation_confidence=relation_confidence, relation_reason=relation_reason)

        self.related_items.add_issue(issue=related_issue)

        self.on_related_item_added(related_issue)

    def add_related_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        comment_id: int,
        relation_confidence: Literal["High", "Medium", "Low"],
        relation_reason: str,
        context: Annotated[str, Field(description="The relevant context from the comment.")],
    ) -> None:
        """Track a GitHub Issue Comment as a related item for the current task."""
        try:
            repository: Repository = self.github_client.get_repo(full_name_or_id=f"{owner}/{repo}")

            issue_comment: IssueComment = repository.get_issue(number=issue_number).get_comment(id=comment_id)
        except Exception as e:
            raise ModelRetry(message=f"Error getting issue comment {owner}/{repo}#{issue_number}#{comment_id}: {e}") from e

        related_issue_comment: RelatedIssueComment = RelatedIssueComment(
            comment=issue_comment,
            context=context,
            relation_confidence=relation_confidence,
            relation_reason=relation_reason,
        )

        self.related_items.add_issue_comment(issue_comment=related_issue_comment)

        self.on_related_item_added(related_issue_comment)

    def add_related_pull_request(
        self, owner: str, repo: str, pull_request_number: int, relation_confidence: Literal["High", "Medium", "Low"], relation_reason: str
    ) -> None:
        """Track a GitHub Pull Request as a related item for the current task."""
        if self._matches_research_issue(owner=owner, repo=repo, issue_number=pull_request_number):
            return

        try:
            repository: Repository = self.github_client.get_repo(full_name_or_id=f"{owner}/{repo}")

            pull_request: PullRequest = repository.get_pull(number=pull_request_number)
        except Exception as e:
            raise ModelRetry(message=f"Error getting pull request {owner}/{repo}#{pull_request_number}: {e}") from e

        related_pull_request: RelatedPullRequest = RelatedPullRequest(
            pull_request=pull_request, relation_confidence=relation_confidence, relation_reason=relation_reason
        )

        self.related_items.add_pull_request(pull_request=related_pull_request)

        self.on_related_item_added(related_pull_request)

    def add_related_file_lines(
        self,
        owner: str,
        repo: str,
        file_path: str,
        branch: str,
        line_numbers: list[FileLineRange],
    ) -> None:
        """Add lines to a related file.

        Useful if you later discover additional lines of an already related file that are related to the issue."""
        if related_file := self.related_items.get_file(owner=owner, repo=repo, file_path=file_path, branch=branch):
            if related_file.line_numbers:
                related_file.line_numbers.extend(line_numbers)
            else:
                related_file.line_numbers = line_numbers

        else:
            msg: str = f"File {file_path} not found in repository {owner}/{repo} on branch {branch}"
            raise ModelRetry(msg)

        self.on_related_item_added(related_file)

    def add_related_file(
        self,
        owner: str,
        repo: str,
        file_path: str,
        relation_confidence: Literal["High", "Medium", "Low"],
        relation_reason: Annotated[
            str, Field(description="The reason you believe there is a relation between the related file and the current issue.")
        ],
        branch: Annotated[str | None, Field(description="The branch to use for the file. If not provided, the default branch is used.")],
        line_numbers: Annotated[
            list[FileLineRange] | None,
            Field(description="The line numbers of the file that are related to the issue. If not provided, the entire file is related."),
        ] = None,
    ) -> None:
        """Track a GitHub File as a related item for the current task."""
        try:
            repository: Repository = self.github_client.get_repo(full_name_or_id=f"{owner}/{repo}")

            file: list[ContentFile] | ContentFile = repository.get_contents(path=file_path, ref=branch or NotSet)
        except Exception as e:
            raise ModelRetry(message=f"Error getting file {owner}/{repo}#{file_path}#{branch or 'default'}: {e}") from e

        if not isinstance(file, list):
            file = [file]

        for f in file:
            related_file: RelatedFile = RelatedFile(
                file=f,
                relation_confidence=relation_confidence,
                relation_reason=relation_reason,
                line_numbers=line_numbers,
            )

            self.related_items.add_file(file=related_file)

            self.on_related_item_added(related_file)

    def add_related_webpage(self, name: str, url: str, relation_confidence: Literal["High", "Medium", "Low"], relation_reason: str) -> None:
        """Track a Webpage as a related item for the current task."""
        related_webpage: RelatedWebpage = RelatedWebpage(
            name=name, url=url, relation_confidence=relation_confidence, relation_reason=relation_reason
        )

        self.related_items.add_webpage(webpage=related_webpage)

        self.on_related_item_added(related_webpage)


def read_only_github_toolset() -> FastMCPServerToolset[Any]:
    github_mcp_server: TransformingStdioMCPServer = repo_restrict_github_mcp(
        issues=True,
        pull_requests=True,
        discussions=True,
        repository=True,
        read_tools=True,
        write_tools=False,
        search_tools=False,
    )

    return FastMCPServerToolset[Any].from_mcp_server(name="github", mcp_server=github_mcp_server)


def read_and_search_github_toolset() -> FastMCPServerToolset[Any]:
    github_mcp_server: TransformingStdioMCPServer = restrict_github_mcp(
        read=True,
        search=True,
    )

    del github_mcp_server.tools["get_file_contents"]

    return FastMCPServerToolset[Any].from_mcp_server(name="github", mcp_server=github_mcp_server)
