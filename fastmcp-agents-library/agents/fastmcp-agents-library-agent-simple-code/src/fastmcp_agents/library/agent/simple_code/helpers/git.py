import os
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import git


@contextmanager
def quick_clone_git_repo(git_url: str, set_cwd: bool = True, delete_on_exit: bool = True) -> Generator[Path]:
    """Quickly clone a git repository."""

    current_cwd = Path.cwd()

    with tempfile.TemporaryDirectory(dir=Path.cwd(), delete=delete_on_exit) as temp_dir:
        _ = git.Repo.clone_from(git_url, temp_dir, single_branch=True, depth=1)

        repo_path = Path(temp_dir)

        if set_cwd:
            os.chdir(repo_path)

        try:
            yield repo_path
        finally:
            if set_cwd:
                os.chdir(current_cwd)
