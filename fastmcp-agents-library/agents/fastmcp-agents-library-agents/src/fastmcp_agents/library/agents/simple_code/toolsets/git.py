import shutil
from contextlib import ExitStack
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Self, override

from git import Repo
from pydantic_ai.tools import AgentDepsT
from pydantic_ai.toolsets import WrapperToolset
from pydantic_ai.toolsets.combined import CombinedToolset

from fastmcp_agents.bridge.pydantic_ai.toolset import FastMCPClientToolset
from fastmcp_agents.library.mcp.modelcontextprotocol.git import TransformingStdioMCPServer, repo_path_restricted_git_mcp_server
from fastmcp_agents.library.mcp.strawgate.filesystem_operations import read_only_filesystem_mcp, read_write_filesystem_mcp


class BaseGitRepositoryToolset(WrapperToolset[AgentDepsT]):
    """A base class for git repository toolsets."""

    code_base: Path

    read_only: bool

    git_tools: bool

    def _filesystem_mcp_server(self) -> TransformingStdioMCPServer:
        if self.read_only:
            return read_only_filesystem_mcp(root_dir=self.code_base)

        return read_write_filesystem_mcp(root_dir=self.code_base)

    def _filesystem_toolset(self) -> FastMCPClientToolset[AgentDepsT]:
        return FastMCPClientToolset[AgentDepsT].from_mcp_server(name="filesystem", mcp_server=self._filesystem_mcp_server())
        # return FastMCPServerToolset[AgentDepsT].from_mcp_server(name="filesystem", mcp_server=self._filesystem_mcp_server())

    def _git_mcp_server(self) -> TransformingStdioMCPServer:
        return repo_path_restricted_git_mcp_server(
            repo_path=self.code_base,
            repository=True,
            commit=True,
            branching=True,
            read_tools=True,
            write_tools=not self.read_only,
        )

    def _git_toolset(self) -> FastMCPClientToolset[AgentDepsT]:
        return FastMCPClientToolset[AgentDepsT].from_mcp_server(name="git", mcp_server=self._git_mcp_server())

    def _toolset(self) -> CombinedToolset[AgentDepsT]:
        toolsets = [self._filesystem_toolset()]
        if self.git_tools:
            toolsets.append(self._git_toolset())

        return CombinedToolset[AgentDepsT](toolsets=toolsets)

    @override
    async def __aenter__(self) -> Self:
        self.wrapped = self._toolset()

        await self.wrapped.__aenter__()

        return self

    @override
    async def __aexit__(self, *args: Any) -> bool | None:
        if self.wrapped:
            return await self.wrapped.__aexit__(*args)

        return None


class LocalGitRepositoryToolset(BaseGitRepositoryToolset[AgentDepsT]):
    """A toolset for git operations."""

    def __init__(self, code_base: Path, read_only: bool = True, git_tools: bool = False):
        self.code_base = code_base
        self.read_only = read_only
        self.git_tools = git_tools


class RemoteGitRepositoryToolset(BaseGitRepositoryToolset[AgentDepsT]):
    """A toolset for git operations."""

    git_url: str
    git_branch: str

    def __init__(
        self,
        git_url: str,
        git_branch: str,
        path: Path | None = None,
        read_only: bool = True,
        git_tools: bool = False,
    ):
        self.git_url = git_url
        self.git_branch = git_branch

        self.read_only = read_only
        self.git_tools = git_tools

        self.code_base = path or Path(mkdtemp())

        self.cloned = False
        self.enter_count = 0

        self._exitstack = ExitStack()

    @override
    async def __aenter__(self) -> Self:
        try:
            if self.enter_count == 0:
                Repo.clone_from(url=self.git_url, to_path=self.code_base, branch=self.git_branch, single_branch=True, depth=1)

            await super().__aenter__()

        except Exception:
            self.cleanup()
            raise

        self.enter_count += 1
        return self

    @override
    async def __aexit__(self, *args: Any) -> bool | None:
        exit_result = await super().__aexit__(*args)

        self.enter_count -= 1

        if self.enter_count == 0:
            self.cleanup()

        return exit_result

    def cleanup(self) -> None:
        if not self.code_base.exists():
            return

        shutil.rmtree(self.code_base)

    def __del__(self) -> None:
        self.cleanup()


# class RemoteGitRepositoryToolset(WrapperToolset[AgentDepsT]):
#     """A toolset for git operations."""

#     git_url: str
#     git_branch: str

#     read_only: bool
#     git_tools: bool

#     code_base: Path

#     _exitstack: ExitStack

#     def __init__(self, git_url: str, git_branch: str, read_only: bool = True, git_tools: bool = False):
#         self.git_url = git_url
#         self.git_branch = git_branch

#         self.read_only = read_only
#         self.git_tools = git_tools

#         self.code_base = Path(mkdtemp())

#         self._exitstack = ExitStack()

#     def _filesystem_mcp_server(self) -> TransformingStdioMCPServer:
#         if self.read_only:
#             return read_only_filesystem_mcp(root_dir=self.code_base)

#         return read_write_filesystem_mcp(root_dir=self.code_base)

#     def _filesystem_toolset(self) -> FastMCPServerToolset[AgentDepsT]:
#         return FastMCPServerToolset[AgentDepsT].from_mcp_server(name="filesystem", mcp_server=self._filesystem_mcp_server())

#     def _git_mcp_server(self) -> TransformingStdioMCPServer:
#         return repo_path_restricted_git_mcp_server(
#             repo_path=self.code_base,
#             repository=True,
#             commit=True,
#             branching=True,
#             read_tools=True,
#             write_tools=not self.read_only,
#         )

#     def _git_toolset(self) -> FastMCPServerToolset[AgentDepsT]:
#         return FastMCPServerToolset[AgentDepsT].from_mcp_server(name="git", mcp_server=self._git_mcp_server())

#     def _toolset(self) -> CombinedToolset[AgentDepsT]:
#         toolsets = [self._filesystem_toolset()]
#         if self.git_tools:
#             toolsets.append(self._git_toolset())

#         return CombinedToolset[AgentDepsT](toolsets=toolsets)

#     @override
#     async def __aenter__(self) -> Self:
#         code_base_str = self._exitstack.enter_context(TemporaryDirectory(dir=self.code_base))

#         self.code_base = Path(code_base_str)

#         Repo.clone_from(url=self.git_url, to_path=self.code_base, branch=self.git_branch, single_branch=True, depth=1)

#         self.wrapped = self._toolset()

#         await self.wrapped.__aenter__()

#         return self

#     @override
#     async def __aexit__(self, *args: Any) -> bool | None:
#         exit_result = await self.wrapped.__aexit__(*args)
#         self._exitstack.close()

#         return exit_result
