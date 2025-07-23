import os
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from git import Repo
import git


def quick_clone_git_repo(target_dir: Path, git_url: str) -> Repo:
    """Quickly clone a git repository."""

    return git.Repo.clone_from(url=git_url, to_path=target_dir, single_branch=True, depth=1)
