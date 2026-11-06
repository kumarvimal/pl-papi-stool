"""Product API Stool settings."""

from stool.settings import create_env

env = create_env(
    default_port=8000,
    worktree_symlink=[
        "_stool",
        ".env",
        ".venv",
        "tasks.py",
        "returns/static/ui/_build",
    ],
    worktree_copy=[],
)
