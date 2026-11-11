"""Offline adapter qualification must precede any framework hook execution."""

from __future__ import annotations

import sqlite3
from contextlib import closing
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.engineering.repo import offline_precommit as adapter

pytestmark = pytest.mark.unit


def test_framework_error_does_not_escape_with_private_exception_text():
    private = "private-exception-sentinel"
    with pytest.raises(adapter.BootstrapRequired) as caught:
        with adapter._quiet_errors():
            raise RuntimeError(private)
    assert private not in str(caught.value)
    assert str(caught.value) == "framework_execution_unavailable"


def test_unknown_framework_never_imports_or_runs_main(monkeypatch, tmp_path):
    monkeypatch.setattr(adapter.importlib.metadata, "version", lambda _: "4.8.0")
    probe = Mock(side_effect=AssertionError("must not inspect unqualified framework"))
    monkeypatch.setattr(adapter, "_qualified_contract", probe)
    assert adapter.run("pre-commit", tmp_path, []) == 2
    probe.assert_not_called()


def test_framework_contract_matches_installed_qualified_version():
    if adapter.importlib.metadata.version("pre-commit") != adapter.QUALIFIED_VERSION:
        pytest.skip("exact framework contract unavailable")
    assert adapter._qualified_contract()


def test_missing_cache_is_not_created(tmp_path):
    cache = tmp_path / "missing"
    with pytest.raises(adapter.BootstrapRequired, match="cache_missing"):
        adapter._store_init(SimpleNamespace(), str(cache))
    assert not cache.exists()


def test_missing_cached_repository_never_calls_clone(tmp_path):
    database = tmp_path / "db.db"
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("CREATE TABLE repos (repo TEXT, ref TEXT, path TEXT)")
    store = SimpleNamespace(db_path=str(database), db_repo_name=lambda repo, deps: repo)
    clone = Mock(side_effect=AssertionError("network bootstrap must not run"))
    with pytest.raises(adapter.BootstrapRequired, match="repository_cache_missing"):
        adapter._cached_repo(store, "fixture", "v1", [], clone)
    clone.assert_not_called()
    with closing(sqlite3.connect(database)) as connection, connection:
        assert connection.execute("SELECT count(*) FROM repos").fetchone() == (0,)


def test_existing_repository_is_read_only(tmp_path):
    database = tmp_path / "db.db"
    cached = tmp_path / "cached"
    cached.mkdir()
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("CREATE TABLE repos (repo TEXT, ref TEXT, path TEXT)")
        connection.execute(
            "INSERT INTO repos VALUES (?, ?, ?)", ("fixture", "v1", str(cached))
        )
    before = database.read_bytes()
    store = SimpleNamespace(db_path=str(database), db_repo_name=lambda repo, deps: repo)
    assert adapter._cached_repo(store, "fixture", "v1", [], Mock()) == str(cached)
    assert database.read_bytes() == before


@pytest.mark.parametrize("healthy", [False, True])
def test_environments_are_checked_without_install(monkeypatch, healthy):
    import pre_commit.repository

    monkeypatch.setattr(pre_commit.repository, "_hook_installed", lambda hook: healthy)
    installer = Mock(side_effect=AssertionError("install must not run"))
    monkeypatch.setattr(pre_commit.repository, "_hook_install", installer)
    if healthy:
        adapter._require_environments([object()], object())
    else:
        with pytest.raises(adapter.BootstrapRequired, match="environment_missing"):
            adapter._require_environments([object()], object())
    installer.assert_not_called()


def test_public_hook_protocol_and_patches_are_restored(monkeypatch, tmp_path):
    import pre_commit.main
    from pre_commit.store import Store

    original = Store.__init__
    observed = []

    def fake_main(argv):
        observed.extend(argv)
        assert Store.__init__ is adapter._store_init
        return 1

    monkeypatch.setattr(pre_commit.main, "main", fake_main)
    monkeypatch.setattr(
        adapter.importlib.metadata, "version", lambda _: adapter.QUALIFIED_VERSION
    )
    assert adapter.run("pre-push", tmp_path, ["origin", "fixture path"]) == 1
    assert observed == [
        "hook-impl",
        "--config",
        ".pre-commit-config.yaml",
        "--hook-type",
        "pre-push",
        "--hook-dir",
        str(tmp_path),
        "--",
        "origin",
        "fixture path",
    ]
    assert Store.__init__ is original


@pytest.mark.parametrize("language,expected", [("system", 0), ("python", 2)])
def test_real_framework_runs_cached_system_checks_but_never_installs(
    tmp_path, language, expected
):
    """The synthetic repository contains only a tiny fixture, no project checkout."""
    root = tmp_path / "fixture with spaces"
    root.mkdir()
    hooks = root / "disabled-hooks"
    hooks.mkdir()
    env = dict(os.environ, PRE_COMMIT_HOME=str(root / "cache"))
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(key, None)

    def git(*args):
        return subprocess.run(
            [
                "git",
                "-c",
                f"core.hooksPath={hooks}",
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                *args,
            ],
            cwd=root,
            env=env,
            capture_output=True,
            check=True,
            timeout=10,
        )

    git("init")
    (root / "fixture.txt").write_text("fixture\n")
    git("add", "fixture.txt")
    git("commit", "-m", "fixture")
    marker = root / "executed.txt"
    import json

    config = {
        "repos": [
            {
                "repo": "local",
                "hooks": [
                    {
                        "id": "fixture",
                        "name": "fixture",
                        "language": language,
                        "entry": f"\"{sys.executable}\" -c \"from pathlib import Path; Path('executed.txt').write_text('ok')\"",
                        "always_run": True,
                        "pass_filenames": False,
                    }
                ],
            }
        ],
    }
    (root / ".pre-commit-config.yaml").write_text(json.dumps(config))
    git("add", ".pre-commit-config.yaml")
    cache = root / "cache"
    cache.mkdir()
    with closing(sqlite3.connect(cache / "db.db")) as connection, connection:
        connection.execute("CREATE TABLE repos (repo TEXT, ref TEXT, path TEXT)")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(Path(adapter.__file__).resolve()),
            "pre-commit",
            str(hooks),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == expected, result.stdout.decode(errors="replace")
    assert marker.exists() is (language == "system")
    assert sorted(path.name for path in cache.iterdir()) == ["db.db"]
