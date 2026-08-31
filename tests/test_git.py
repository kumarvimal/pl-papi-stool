from pathlib import Path

from _stool import git


def test_link_local_paths_creates_missing_target_parent(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    source = root / "returns/static/ui/_build"
    source.mkdir(parents=True)
    worktree.mkdir()

    linked = git._link_local_paths(root, worktree)

    target = worktree / "returns/static/ui/_build"
    assert linked == ["returns/static/ui/_build"]
    assert target.is_symlink()
    assert target.resolve() == source


def test_create_worktree_repairs_links_for_existing_worktree(
    monkeypatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    root.mkdir()
    (root / ".env").touch()
    worktree.mkdir()

    monkeypatch.setattr(git, "_validate_branch", lambda branch: None)
    monkeypatch.setattr(git, "_repo_root", lambda: root)
    monkeypatch.setattr(git, "_linked_worktree_for_branch", lambda branch: worktree)

    result = git._create_worktree("feature")

    assert result == (
        f"feature already has a worktree at {worktree}\nlinked local paths: .env\n"
    )
    assert (worktree / ".env").is_symlink()
