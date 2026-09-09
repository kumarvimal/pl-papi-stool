from _stool import npm


def test_update_zprofile_replaces_literal_token() -> None:
    content = "export FOO=bar\nexport NPM_GITHUB_TOKEN=secret\n"

    updated = npm._update_zprofile(content)

    assert "secret" not in updated
    assert "export FOO=bar" in updated
    assert updated.count(npm.MANAGED_BLOCK_START) == 1
    assert 'NPM_GITHUB_TOKEN="$(gh auth token' in updated


def test_update_zprofile_is_idempotent() -> None:
    updated = npm._update_zprofile("")

    assert npm._update_zprofile(updated) == updated
