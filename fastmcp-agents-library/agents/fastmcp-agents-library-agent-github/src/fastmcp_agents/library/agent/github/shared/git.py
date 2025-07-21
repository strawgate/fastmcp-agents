import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import git


def get_repo_url(owner: str, repository: str) -> str:
    return f"https://github.com/{owner}/{repository}.git"


@contextmanager
def quick_clone_github_repo(owner: str, repository: str) -> Generator[Path]:
    repo_url = f"https://github.com/{owner}/{repository}.git"

    with tempfile.TemporaryDirectory() as temp_dir:
        _ = git.Repo.clone_from(repo_url, temp_dir, single_branch=True, depth=1)

        yield Path(temp_dir)
