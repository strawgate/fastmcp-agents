from collections.abc import Generator
from pathlib import Path
from typing import Literal, Self

from git.repo import Repo
from pydantic import AnyHttpUrl, BaseModel, Field, computed_field, model_validator


class FileLine(BaseModel):
    """A file line with line number and content."""

    line: int = Field(default=..., description="The line number of the file, indexed from 1.")
    content: str = Field(default=..., description="The content of the line.")


class InvestigationFinding(BaseModel):
    """An investigation finding."""

    description: str
    file_path: str | None = None
    lines: list[FileLine] = Field(default=..., description="The relevant lines of code in the file with their line numbers.")


class InvestigationRecommendation(BaseModel):
    """An investigation recommendation."""

    description: str
    action: Literal["fix", "refactor", "propose", "implement"]
    file_path: str | None = None
    current_lines: list[FileLine] = Field(default=..., description="The relevant lines of code in the file with their line numbers.")
    proposed_lines: list[FileLine] = Field(default=..., description="The proposed lines of code in the file with their line numbers.")


class DirectoryStructure(BaseModel):
    """A directory structure."""

    results: list[str]
    max_results: int = Field(description="The maximum number of results to return.", exclude=True)

    @computed_field
    @property
    def limit_reached(self) -> bool:
        """Check if the limit has been reached."""

        return len(self.results) >= self.max_results

    @classmethod
    def from_dir(cls, directory: Path, max_results: int = 150) -> Self:
        results: list[str] = []

        for item in _limited_depth_iterdir(path=directory, max_depth=3):
            if len(results) >= max_results:
                break
            if item.is_file():
                results.append(item.name)
            elif item.is_dir():
                results.append(item.name + "/")

        return cls(results=results, max_results=max_results)


def _limited_depth_iterdir(
    path: Path,
    max_depth: int = 3,
    current_depth: int = 0,
) -> Generator[Path]:
    """
    Iterates through directory contents up to a specified maximum depth.

    Args:
        path (Path): The starting directory path.
        max_depth (int): The maximum depth to traverse (0 for current directory only).
        current_depth (int): The current depth during recursion (internal use).

    Yields:
        Path: A path object for each file or directory within the depth limit.
    """
    if current_depth > max_depth:
        return

    for item in path.iterdir():
        yield item
        if item.is_dir():
            yield from _limited_depth_iterdir(path=item, max_depth=max_depth, current_depth=current_depth + 1)


class BranchInfo(BaseModel):
    """A repository info."""

    name: str
    commit_sha: str

    @classmethod
    def from_repo(cls, repo: Repo) -> "BranchInfo":
        """Create a branch info from a repository."""
        return cls(name=repo.active_branch.name, commit_sha=repo.head.commit.hexsha)

    @classmethod
    def from_dir(cls, directory: Path) -> "BranchInfo | None":
        """Create a branch info from a directory."""
        try:
            repo: Repo = Repo(path=directory)
            return cls.from_repo(repo)
        except Exception:
            return None


class InvestigationResult(BaseModel):
    """An investigation result."""

    summary: str = Field(default=..., description="A summary of the findings. Under 1 page.")
    branch_info: BranchInfo | None = Field(default=None, description="The branch info of the repository.")
    confidence: Literal["high", "medium", "low"] = Field(default=..., description="The confidence of the findings.")
    findings: list[InvestigationFinding]
    recommendations: list[InvestigationRecommendation] = Field(
        default=..., description="Recommendations for next steps based on the findings."
    )


class PotentialFlaw(BaseModel):
    """A potential flaw in the code."""

    description: str
    file_path: str | None = None
    lines: list[FileLine] = Field(default=..., description="The relevant lines of code in the file with their line numbers.")


class ImplementationResponse(BaseModel):
    """A response from the implementation agent."""

    summary: str
    confidence: Literal["low", "medium", "high"]
    potential_flaws: list[PotentialFlaw] = Field(
        default=..., description="A list of potential flaws in the code that a reviewer should review before merging."
    )


class CodeAgentInput(BaseModel):
    local_directory: Path | None = None
    git_repository: AnyHttpUrl | None = None

    @model_validator(mode="after")
    def validate_input(self) -> Self:
        if self.local_directory is None and self.git_repository is None:
            msg = "Either local_directory or git_repository must be provided."
            raise ValueError(msg)
        if self.local_directory is not None and self.git_repository is not None:
            msg = "Only one of local_directory or git_repository must be provided."
            raise ValueError(msg)
        return self
