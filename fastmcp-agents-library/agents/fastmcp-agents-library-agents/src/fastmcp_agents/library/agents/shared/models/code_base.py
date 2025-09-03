from pathlib import Path
from tempfile import mkdtemp
from typing import Any

from git.repo import Repo
from pydantic import BaseModel, Field, PrivateAttr

from fastmcp_agents.library.agents.simple_code.toolsets.git import BaseGitRepositoryToolset


class BaseCodeBase(BaseModel):
    """A dependency on a code base."""

    _path: Path | None = PrivateAttr(default=None)

    @property
    def path(self) -> Path:
        if self._path is None:
            msg = "Code base not been set yet."
            raise ValueError(msg)

        return self._path

    @path.setter
    def path(self, value: Path):
        self._path = value

    def diff(self) -> str | None:
        """Get the diff of the code base."""
        msg = "Diff should be implemented by the subclass."
        raise NotImplementedError(msg)

    def to_toolset(self, read_only: bool = True, git_tools: bool = True) -> BaseGitRepositoryToolset[Any]:
        msg = "Code base toolset is not implemented."
        raise NotImplementedError(msg)

    def is_dirty(self) -> bool:
        """Check if the code base is dirty."""
        return False


class FilesystemCodeBase(BaseCodeBase):
    """A code base that is just a directory on the filesystem."""

    def to_toolset(self, read_only: bool = True, git_tools: bool = True) -> BaseGitRepositoryToolset[Any]:
        msg = "Filesystem code base toolset is not implemented."
        raise NotImplementedError(msg)

    def is_dirty(self) -> bool:
        """Check if the code base is dirty."""
        return False

    def diff(self) -> str | None:
        """Get the diff of the code base. Returns None with the FilesystemCodeBase."""
        return None


class BaseGitCodeBase(BaseCodeBase):
    """A code base that is a git repository."""

    def _repository(self) -> Repo:
        """Get the git repository."""
        return Repo(self.path)

    # def git_diff(self) -> str | None:
    #     """Get the diff of the code base."""
    #     t = self._repository().head.commit.tree

    #     return self._repository().git.diff(t)

    # def git_is_dirty(self) -> bool:
    #     """Check if there are uncommitted changes in the code base."""

    #     return self._repository().is_dirty()

    def is_dirty(self) -> bool:
        """Check if the code base is dirty."""
        return self._repository().is_dirty()

    def diff(self) -> str | None:
        """Get the diff of the code base."""
        t = self._repository().head.commit.tree
        return self._repository().git.diff(t)


class GitCodeBase(BaseGitCodeBase, BaseModel):
    """A code base that is a git repository."""

    def __init__(self, path: Path):
        super().__init__()
        self.path = path

    def to_toolset(self, read_only: bool = True, git_tools: bool = True) -> BaseGitRepositoryToolset[Any]:
        from fastmcp_agents.library.agents.simple_code.toolsets.git import LocalGitRepositoryToolset

        return LocalGitRepositoryToolset[Any](
            code_base=self.path,
            read_only=read_only,
            git_tools=git_tools,
        )


class RemoteGitCodeBase(BaseGitCodeBase, BaseModel):
    """A code base that is a remote git repository."""

    git_url: str = Field(description="The URL of the git repository to use for the Agent.")
    git_branch: str = Field(description="The branch of the git repository to use for the Agent.")

    _path: Path | None = PrivateAttr(default_factory=lambda: Path(mkdtemp()))

    def clone(self) -> None:
        """Clone the git repository."""
        Repo.clone_from(url=self.git_url, to_path=self.path, branch=self.git_branch, single_branch=True, depth=1)

    def to_toolset(self, read_only: bool = True, git_tools: bool = True) -> BaseGitRepositoryToolset[Any]:
        from fastmcp_agents.library.agents.simple_code.toolsets.git import RemoteGitRepositoryToolset

        return RemoteGitRepositoryToolset[Any](
            git_url=self.git_url,
            git_branch=self.git_branch,
            path=self.path,
            read_only=read_only,
            git_tools=git_tools,
        )


# class RemoteGitRepository(BaseModel):
#     git_url: str = Field(description="The URL of the git repository to use for the Agent.")
#     git_branch: str = Field(description="The branch of the git repository to use for the Agent.")


# class LocalGitRepository(BaseModel):
#     git_path: Path = Field(description="The code base to use for the Agent.")


# class GitRepositoryDependency(BaseModel):
#     """A dependency on a git repository."""

#     git_repository: RemoteGitRepository | LocalGitRepository = Field(
#         description="The git repository to use for the Agent.",
#     )

#     def to_git_repository_toolset(self, read_only: bool = True, git_tools: bool = True) -> BaseGitRepositoryToolset[Any]:
#         from fastmcp_agents.library.agents.simple_code.toolsets.git import LocalGitRepositoryToolset, RemoteGitRepositoryToolset

#         if isinstance(self.git_repository, RemoteGitRepository):
#             toolset = RemoteGitRepositoryToolset[Any](
#                 git_url=self.git_repository.git_url,
#                 git_branch=self.git_repository.git_branch,
#                 read_only=read_only,
#                 git_tools=git_tools,
#             )
#         else:
#             toolset = LocalGitRepositoryToolset[Any](
#                 code_base=self.git_repository.git_path,
#                 read_only=read_only,
#                 git_tools=git_tools,
#             )

#         return toolset
