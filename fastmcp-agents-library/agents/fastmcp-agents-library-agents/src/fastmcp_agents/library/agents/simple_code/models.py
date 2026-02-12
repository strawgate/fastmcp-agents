from pydantic import BaseModel, Field

# class InvestigationRecommendation(BaseModel):
#     """An investigation recommendation."""

#     description: str
#     action: Literal["fix", "refactor", "propose", "implement"]
#     file_path: str | None = None
#     current_lines: FileLines = Field(default=..., description="The relevant lines of code in the file with their line numbers.")
#     proposed_lines: FileLines = Field(default=..., description="The proposed lines of code in the file with their line numbers.")


# class DirectoryStructure(BaseModel):
#     """A directory structure."""

#     results: list[str]
#     max_results: int = Field(description="The maximum number of results to return.", exclude=True)

#     @computed_field
#     @property
#     def limit_reached(self) -> bool:
#         """Check if the limit has been reached."""

#         return len(self.results) >= self.max_results

#     @classmethod
#     def from_dir(cls, directory: Path, max_results: int = 150) -> Self:
#         results: list[str] = []

#         for item in _limited_depth_iterdir(root=directory, path=directory, max_depth=3):
#             if len(results) >= max_results:
#                 break
#             if item.name.startswith("."):
#                 continue
#             if item.is_file():
#                 results.append(item.relative_to(directory).as_posix())
#             elif item.is_dir():
#                 results.append(item.relative_to(directory).as_posix() + "/")

#         return cls(results=results, max_results=max_results)

#     def as_yaml(self) -> str:
#         """Convert the directory structure to a YAML string."""
#         return yaml.safe_dump(self.model_dump())


# def _limited_depth_iterdir(
#     root: Path,
#     path: Path,
#     max_depth: int = 3,
#     current_depth: int = 0,
# ) -> Generator[Path]:
#     """
#     Iterates through directory contents up to a specified maximum depth.

#     Args:
#         path (Path): The starting directory path.
#         max_depth (int): The maximum depth to traverse (0 for current directory only).
#         current_depth (int): The current depth during recursion (internal use).

#     Yields:
#         Path: A path object for each file or directory within the depth limit.
#     """
#     if current_depth > max_depth:
#         return

#     for item in path.iterdir():
#         resolved_item = item.resolve()
#         yield resolved_item
#         if item.name.startswith("."):
#             continue
#         if item.is_dir():
#             yield from _limited_depth_iterdir(root=root, path=resolved_item, max_depth=max_depth, current_depth=current_depth + 1)


# class BranchInfo(BaseModel):
#     """A repository info."""

#     name: str
#     commit_sha: str

#     @classmethod
#     def from_repo(cls, repo: Repo) -> "BranchInfo":
#         """Create a branch info from a repository."""
#         return cls(name=repo.active_branch.name, commit_sha=repo.head.commit.hexsha)

#     @classmethod
#     def from_dir(cls, directory: Path) -> "BranchInfo | None":
#         """Create a branch info from a directory."""
#         try:
#             repo: Repo = Repo(path=directory)
#             return cls.from_repo(repo)
#         except Exception:
#             return None


# class NoFlaws(BaseModel):
#     """Indicates that no flaws were found in the code implementation."""

#     compliment: str = Field(
#         description="A compliment for the Agent for a job well done.",
#     )


class CodeChange(BaseModel):
    """A code change."""

    file_path: str = Field(description="The path to the file that is being changed.")
    description: str = Field(description="A friendly description of the changes or findings.")


class CodeAgentResponse(BaseModel):
    """A response from the implementation agent."""

    summary: str
    code_diff: str | None = Field(
        default=None,
        description=(
            "The git diff of the changes that were made by the Agent. If the changes were not made in a git repository, this will be None."
        ),
    )
    code_changes: list[CodeChange] | None = Field(default=None, description="The code changes that were made by the Agent.")
