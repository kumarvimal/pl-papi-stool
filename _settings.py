"""Product API worktree setup."""

from stool.settings import create_env

env = create_env(
    worktree_symlink=[
        "_stool",
        ".env",
        ".venv",
        "tasks.py",
        "returns/static/ui/_build",
    ],
    worktree_copy=[],
)
