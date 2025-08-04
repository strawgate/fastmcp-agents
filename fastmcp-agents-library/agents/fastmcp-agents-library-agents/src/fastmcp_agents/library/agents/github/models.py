from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field


class GitHubIssue(BaseModel):
    owner: str = Field(description="The owner of the repository.")
    repo: str = Field(description="The name of the repository.")
    issue_number: int = Field(description="The number of the issue.")

    title: str | None = Field(default=None, description="The title of the issue.")

    def repository_url(self) -> AnyHttpUrl:
        return AnyHttpUrl(url=f"https://github.com/{self.owner}/{self.repo}")

    def repository_git_url(self) -> AnyHttpUrl:
        return AnyHttpUrl(url=f"https://github.com/{self.owner}/{self.repo}.git")


class GitHubRelatedIssue(GitHubIssue):
    relation_confidence: Literal["high", "medium", "low"] = Field(
        description="The confidence in the relation between the related issue and the current issue."
    )
    relation_reason: str = Field(description="The reason you believe there is a relation between the related issue and the current issue.")


class GitHubIssueSummary(GitHubIssue):
    detailed_summary: str = Field(description="A detailed summary of the issue.")
    related_issues: list[GitHubRelatedIssue] = Field(description="A list of related issues.")
