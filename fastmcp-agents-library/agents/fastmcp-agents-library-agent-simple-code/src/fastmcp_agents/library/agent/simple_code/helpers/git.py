from pathlib import Path

import git
from git import Repo


def quick_clone_git_repo(target_dir: Path, git_url: str) -> Repo:
    """Quickly clone a git repository."""

    return git.Repo.clone_from(url=git_url, to_path=target_dir, single_branch=True, depth=1)
