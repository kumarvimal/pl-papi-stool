from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import invoke

DEFAULT_BRANCH_COUNT = 4
LOCAL_LINKS = ("_stool", ".env", ".venv", "tasks.py", "returns/static/ui/_build")


def _latest_branches(number: int) -> str:
    if number < 1:
        raise ValueError("number must be greater than 0")

    result = subprocess.run(
        [
            "git",
            "for-each-ref",
            f"--count={number}",
            "--sort=-committerdate",
            "--format=%(committerdate:relative)%09%(refname:short)",
            "refs/heads",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _git_stdout(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repo_root() -> Path:
    return Path(_git_stdout("rev-parse", "--show-toplevel"))


def _branch_exists(branch: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        check=False,
    )
    return result.returncode == 0


def _validate_branch(branch: str) -> None:
    subprocess.run(["git", "check-ref-format", "--branch", branch], check=True)


def _safe_worktree_name(root: Path, branch: str) -> str:
    suffix = re.sub(r"[^A-Za-z0-9._-]+", "-", branch.replace("/", "-"))
    return f"{root.name}-{suffix.strip('.-')}"


def _default_worktree_path(root: Path, branch: str) -> Path:
    return root.parent / _safe_worktree_name(root, branch)


def _linked_worktree_for_branch(branch: str) -> Path | None:
    entries = _worktrees()
    ref = f"refs/heads/{branch}"
    for entry in entries:
        if entry.get("branch") == ref:
            return Path(entry["worktree"])
    return None


def _link_local_paths(root: Path, worktree_path: Path) -> list[str]:
    linked = []
    for name in LOCAL_LINKS:
        source = root / name
        target = worktree_path / name
        if not source.exists() or target.exists() or target.is_symlink():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, target_is_directory=source.is_dir())
        linked.append(name)
    return linked


def _create_worktree(branch: str, path: str | None = None) -> str:
    _validate_branch(branch)
    root = _repo_root()
    worktree_path = (
        Path(path).expanduser() if path else _default_worktree_path(root, branch)
    )
    worktree_path = worktree_path.resolve()

    existing_path = _linked_worktree_for_branch(branch)
    if existing_path is not None:
        linked = _link_local_paths(root, existing_path)
        linked_text = ", ".join(linked) if linked else "none"
        return (
            f"{branch} already has a worktree at {existing_path}\n"
            f"linked local paths: {linked_text}\n"
        )

    command = ["git", "worktree", "add"]
    if not _branch_exists(branch):
        command.extend(["-b", branch])
    command.append(str(worktree_path))
    if _branch_exists(branch):
        command.append(branch)
    subprocess.run(command, check=True)

    linked = _link_local_paths(root, worktree_path)
    linked_text = ", ".join(linked) if linked else "none"
    return f"created {worktree_path}\nlinked local paths: {linked_text}\n"


def _worktrees() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    entry: dict[str, str] = {}
    for line in _git_stdout("worktree", "list", "--porcelain").splitlines():
        if not line:
            entries.append(entry)
            entry = {}
            continue
        key, _, value = line.partition(" ")
        entry[key] = value
    if entry:
        entries.append(entry)
    return entries


def _list_worktrees() -> str:
    lines = []
    for entry in _worktrees():
        branch = entry.get("branch", "detached").removeprefix("refs/heads/")
        path = entry["worktree"]
        lines.append(f"{branch}\t{path}")
    return "\n".join(lines) + "\n"


@invoke.task(aliases=["branches"])
def latest(ctx, number: int = DEFAULT_BRANCH_COUNT) -> None:
    """List the most recently updated local branches"""
    sys.stdout.write(_latest_branches(int(number)))


@invoke.task(aliases=["wt"])
def worktree(ctx, branch: str, path: str | None = None) -> None:
    """Create a git worktree for BRANCH"""
    sys.stdout.write(_create_worktree(branch, path))


@invoke.task(name="list", aliases=["worktrees"])
def list_worktrees(ctx) -> None:
    """List git worktrees"""
    sys.stdout.write(_list_worktrees())
