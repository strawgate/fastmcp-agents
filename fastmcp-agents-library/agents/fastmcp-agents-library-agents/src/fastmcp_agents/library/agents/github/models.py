from typing import Literal

from pydantic import BaseModel


class GitHubRelatedIssue(BaseModel):
    issue_title: str
    issue_number: int
    confidence: Literal["high", "medium", "low"]
    reason: str


class GitHubIssueSummary(BaseModel):
    issue_title: str
    issue_number: int
    detailed_summary: str
    related_issues: list[GitHubRelatedIssue]
