"""Unit tests for branch_hygiene classification helpers."""

from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest

from scripts.engineering.repo import branch_hygiene as bh

pytestmark = pytest.mark.unit


def _stub_os(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bh,
        "os",
        SimpleNamespace(
            stat=lambda p, **kw: SimpleNamespace(st_mtime=0), walk=lambda *a, **k: []
        ),
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("open-pr-1.__trash_20261111", "20261111"),
        ("x.__trash_20260102030405", "20260102"),
        ("plain-dir", None),
        ("__trash_20261111", None),
    ],
)
def test_trash_date(name: str, expected: str | None) -> None:
    assert bh.trash_date(name) == expected


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        (".env", True),
        (".env.local", True),
        ("configs/.env.production", True),
        (".venv/lib/x", True),
        ("pkg/node_modules/lib", True),
        ("src/app.py", False),
        ("docs/report.md", False),
    ],
)
def test_excluded(rel: str, expected: bool) -> None:
    assert bh.excluded(rel) is expected


def _wt(
    path: str, *, branch: str | None, detached: bool = False, locked: str | None = None
) -> dict:
    return {
        "path": path,
        "head": "abc123",
        "branch": branch,
        "detached": detached,
        "locked": locked,
        "prunable": False,
    }


def test_classify_worktrees_never_touches_locked_or_main(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(bh, "git", lambda *a: "1000000")
    monkeypatch.setattr(bh, "status_counts", lambda p: (False, False, True))
    _stub_os(monkeypatch)
    main = _wt(str(bh.REPO), branch="main")
    locked = _wt(str(tmp_path / "wt-locked"), branch="x", locked="recovery")
    clean_detached = _wt(str(tmp_path / "wt-detached"), branch=None, detached=True)
    rows = bh.classify_worktrees(
        [main, locked, clean_detached], [], detached_days=2, branch_days=3
    )
    by_path = {r["path"]: r for r in rows}
    assert by_path[str(bh.REPO)]["action"] == "KEEP"
    assert by_path[str(tmp_path / "wt-locked")]["action"] == "KEEP_LOCKED"
    assert by_path[str(tmp_path / "wt-detached")]["action"] == "REMOVE"


def test_classify_worktrees_archives_dirty_detached(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(bh, "git", lambda *a: "1000000")
    monkeypatch.setattr(bh, "status_counts", lambda p: (True, False, True))
    _stub_os(monkeypatch)
    dirty = tmp_path / "wt-dirty"
    dirty.mkdir()
    wt = _wt(str(dirty), branch=None, detached=True)
    rows = bh.classify_worktrees([wt], [], detached_days=2, branch_days=3)
    assert rows[0]["action"] == "REMOVE_ARCHIVE"


@pytest.mark.parametrize("detached", [True, False])
def test_untracked_only_tree_requires_archive(monkeypatch, tmp_path, detached):
    tree = tmp_path / "untracked-only"
    tree.mkdir()
    monkeypatch.setattr(bh, "_now", lambda: 20 * bh.DAY)
    monkeypatch.setattr(bh, "git", lambda *args: "1")
    monkeypatch.setattr(bh, "status_counts", lambda path: (False, True, True))
    _stub_os(monkeypatch)
    branch = None if detached else "gone"
    branches = (
        [] if detached else [{"name": "gone", "gone": True, "upstream": "origin/gone"}]
    )
    rows = bh.classify_worktrees(
        [_wt(str(tree), branch=branch, detached=detached)], branches, 2, 3
    )
    assert rows[0]["action"] == "REMOVE_ARCHIVE"


@pytest.mark.parametrize("states", [["OPEN", "MERGED"], ["CLOSED", "OPEN"]])
@pytest.mark.parametrize("gone", [True, False])
def test_open_pr_always_keeps_branch(monkeypatch, states, gone):
    monkeypatch.setattr(bh, "pr_state_map", lambda: {"reuse": states})
    branches = [
        {
            "name": "reuse",
            "sha": "abc",
            "upstream": "origin/reuse",
            "gone": gone,
            "tip_ctime": 0,
        }
    ]
    buckets = bh.classify_branches(branches, [], "main", 3)
    assert [row["name"] for row in buckets["E"]] == ["reuse"]
    assert not buckets["A"] and not buckets["B"] and not buckets["C"]


@pytest.mark.parametrize(
    "name",
    ["review.__trash_recovery", "review.__trash_20260230", "review.__trash_20x260101"],
)
def test_unknown_or_invalid_trash_date_is_not_expired(name):
    assert bh.trash_date(name) is None


def test_apply_defaults_to_dry_run(monkeypatch, tmp_path):
    monkeypatch.setattr(
        bh, "_classify_impl", lambda args: pytest.fail("dry run mutated classification")
    )
    assert bh.main(["apply", "--out", str(tmp_path)]) == 0


def test_archive_command_failure_stops_archive(monkeypatch, tmp_path):
    monkeypatch.setattr(
        bh,
        "run",
        lambda args: SimpleNamespace(returncode=1, stdout="", stderr="disk error"),
    )
    with pytest.raises(RuntimeError, match="complete worktree"):
        bh.archive_tree(tmp_path, "tree", "abc", tmp_path / "archive")


def test_nested_env_is_never_copied(monkeypatch, tmp_path):
    # No env file is created: Git output represents an excluded nested input.
    def fake_run(args, **kwargs):
        output = (
            "newdir/.env.production\0"
            if "ls-files" in args
            else (b"" if kwargs.get("binary") else "")
        )
        return SimpleNamespace(returncode=0, stdout=output)

    monkeypatch.setattr(bh, "run", fake_run)
    monkeypatch.setattr(bh.shutil, "copy2", lambda *args: pytest.fail("copied env"))
    with pytest.raises(RuntimeError, match="excluded"):
        bh.archive_tree(tmp_path, "tree", "abc", tmp_path / "archive")


def _apply_fixture(monkeypatch, tmp_path, *, changed=False, archive_error=False):
    import json

    tree = tmp_path / "tree"
    tree.mkdir()
    row = {**_wt(str(tree), branch=None, detached=True), "action": "REMOVE_ARCHIVE"}
    (tmp_path / "classification.json").write_text(
        json.dumps(
            {
                "cutoffs": {"detached_days": 2.0, "branch_days": 3.0},
                "worktrees": [row],
                "orphans": [],
                "branches": {key: [] for key in "ABCDE"},
            }
        )
    )
    monkeypatch.setattr(bh, "_report_directory", lambda value: value)
    monkeypatch.setattr(bh, "_classify_impl", lambda args: tmp_path)
    monkeypatch.setattr(bh, "registered_worktrees", lambda: [])
    monkeypatch.setattr(bh, "local_branches", lambda: [])
    monkeypatch.setattr(
        bh,
        "classify_worktrees",
        lambda *args: [{**row, "head": "new"}] if changed else [row],
    )
    monkeypatch.setattr(bh, "_safe_tree_target", lambda path, **kwargs: path)

    def archive(*args):
        if archive_error:
            raise OSError("disk full")
        return {"complete": True}

    monkeypatch.setattr(bh, "archive_tree", archive)
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(bh, "run", run)
    return calls


@pytest.mark.parametrize("changed,archive_error", [(True, False), (False, True)])
def test_apply_never_removes_changed_or_unarchived_tree(
    monkeypatch, tmp_path, changed, archive_error
):
    calls = _apply_fixture(
        monkeypatch, tmp_path, changed=changed, archive_error=archive_error
    )
    assert bh.main(["apply", "--out", str(tmp_path), "--execute"]) == int(
        archive_error or changed
    )
    assert not any("remove" in args for args in calls)


def test_tree_guard_rejects_nested_env_without_creating_env(monkeypatch, tmp_path):
    monkeypatch.setattr(bh, "GOVERNED_WORKSPACE_ROOT", tmp_path.parent)
    monkeypatch.setattr(
        bh.os,
        "walk",
        lambda *args, **kwargs: [(str(tmp_path), [], [".env.production"])],
    )
    with pytest.raises(RuntimeError, match="env or linked"):
        bh._safe_tree_target(tmp_path)


def test_worktree_removal_uses_git_dirty_protection(monkeypatch, tmp_path):
    calls = _apply_fixture(monkeypatch, tmp_path)
    original = bh.run

    def run(args, **kwargs):
        if "worktree" in args and "remove" in args:
            calls.append(args)
            return SimpleNamespace(
                returncode=1, stdout="", stderr="contains modified files"
            )
        return original(args, **kwargs)

    monkeypatch.setattr(bh, "run", run)
    assert bh.main(["apply", "--out", str(tmp_path), "--execute"]) == 1
    removals = [args for args in calls if "remove" in args]
    assert len(removals) == 1
    assert "--force" not in removals[0]


@pytest.mark.parametrize("use_parent", [False, True])
def test_tree_guard_refuses_parent_or_governed_root(monkeypatch, tmp_path, use_parent):
    root = tmp_path / "workspace"
    root.mkdir()
    monkeypatch.setattr(bh, "GOVERNED_WORKSPACE_ROOT", root)
    target = tmp_path if use_parent else root
    with pytest.raises(RuntimeError, match="outside governed workspace"):
        bh._safe_tree_target(target)


def test_worktree_lock_without_reason_is_preserved(monkeypatch):
    monkeypatch.setattr(
        bh,
        "git",
        lambda *args: (
            "worktree D:/github/locked-fixture\nHEAD abc123\nbranch refs/heads/topic\nlocked\n\n"
        ),
    )
    worktrees = bh.registered_worktrees()
    assert worktrees[0]["locked"] == "locked"


def test_quarantine_destination_must_stay_in_owned_root(monkeypatch, tmp_path):
    root = tmp_path / "worktrees"
    monkeypatch.setattr(bh, "GOVERNED_WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(bh, "WT_ROOT", root)
    bh._safe_quarantine_destination(root / ".__trash_20261113" / "retained")
    with pytest.raises(RuntimeError, match="outside governed|escapes"):
        bh._safe_quarantine_destination(tmp_path / "other-project" / "retained")
    assert not root.exists()


def test_fresh_tip_with_finished_pr_is_not_deleted(monkeypatch):
    monkeypatch.setattr(bh, "_now", lambda: 100 * bh.DAY)
    monkeypatch.setattr(bh, "pr_state_map", lambda: {"renewed": ["MERGED"]})
    branches = [
        {
            "name": "renewed",
            "sha": "new",
            "upstream": "origin/renewed",
            "gone": False,
            "tip_ctime": int(99 * bh.DAY),
        }
    ]
    buckets = bh.classify_branches(branches, [], "main", 3)
    assert [row["name"] for row in buckets["E"]] == ["renewed"]
    assert not buckets["A"]


@pytest.mark.parametrize(
    "command", [[], ["python", "bad.py"], ["sh", "-c", "bad"], ["../git", "status"]]
)
def test_run_rejects_unapproved_executables_before_spawn(monkeypatch, command):
    monkeypatch.setattr(
        bh.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("unapproved process started"),
    )
    with pytest.raises(RuntimeError, match="fixed Git"):
        bh.run(command)


def test_report_directory_is_confined_without_creating_files(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    monkeypatch.setattr(bh, "REPO", root)
    allowed = root / "reports" / "local" / "review"
    assert bh._report_directory(allowed) == allowed.resolve()
    with pytest.raises(RuntimeError, match="outside governed"):
        bh._report_directory(tmp_path / "other-project")
    assert not root.exists()


def test_tree_guard_rejects_env_leaf_before_query(monkeypatch, tmp_path):
    monkeypatch.setattr(bh, "GOVERNED_WORKSPACE_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="env or linked"):
        bh._safe_tree_target(tmp_path / ".env.production")
    assert not (tmp_path / ".env.production").exists()


def test_new_directory_with_old_trash_name_is_not_expired(monkeypatch, tmp_path):
    directory = tmp_path / "review.__trash_20200101"
    directory.mkdir()
    monkeypatch.setattr(bh, "_now", lambda: directory.stat().st_mtime + bh.DAY)
    monkeypatch.setattr(
        bh.shutil, "rmtree", lambda *args: pytest.fail("fresh quarantine removed")
    )
    assert "kept" in bh._delete_trash(directory)


def test_archive_rejects_deleted_tracked_env_before_reading_diff(monkeypatch, tmp_path):
    def run(args):
        assert "--name-only" in args, "must not read excluded tracked file contents"
        return SimpleNamespace(returncode=0, stdout=".env.example\0", stderr="")

    monkeypatch.setattr(bh, "run", run)
    with pytest.raises(RuntimeError, match="excluded tracked"):
        bh.archive_tree(tmp_path, "tree", "abc", tmp_path / "archive")
    assert not (tmp_path / "archive").exists()


def test_archive_preserves_index_bytes_unicode_names_and_previous_snapshots(
    monkeypatch, tmp_path
):
    source = tmp_path / "tree"
    source.mkdir()
    (source / "café.txt").write_bytes(b"untracked\r\n")
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if "ls-files" in args:
            value = "café.txt\0"
        elif kwargs.get("binary"):
            value = b"index\r\n" if "--cached" in args else b"working\r\n"
        else:
            value = ""
        return SimpleNamespace(returncode=0, stdout=value)

    monkeypatch.setattr(bh, "run", fake_run)
    archive = tmp_path / "archive"
    first = bh.archive_tree(source, "tree", "abc", archive)
    second = bh.archive_tree(source, "tree", "def", archive)
    one, two = Path(first["archive"]), Path(second["archive"])
    assert one != two
    for snapshot in (one, two):
        assert (snapshot / "index.patch").read_bytes() == b"index\r\n"
        assert (snapshot / "working.patch").read_bytes() == b"working\r\n"
        assert (snapshot / "untracked" / "café.txt").read_bytes() == b"untracked\r\n"
    assert (one / "head.txt").read_text() == "abc tree\n"
    patch_calls = [args for args in calls if "--binary" in args]
    assert len(patch_calls) == 4
    assert all(
        "--no-ext-diff" in args and "--no-textconv" in args for args in patch_calls
    )


@pytest.mark.parametrize("name", ["main", "master", "master_202607-recovery"])
def test_protected_branches_never_enter_deletion_buckets(monkeypatch, name):
    monkeypatch.setattr(bh, "pr_state_map", lambda: {})
    monkeypatch.setattr(bh, "cherry_unique", lambda name: 10)
    row = {"name": name, "sha": "abc", "upstream": "", "gone": True, "tip_ctime": 0}
    buckets = bh.classify_branches([row], [], "HEAD", 3)
    assert [item["name"] for item in buckets["D"]] == [name]
    assert bh._deletion_candidates(buckets) == []


def test_recent_nested_file_keeps_old_dirty_tree(monkeypatch, tmp_path):
    tree = tmp_path / "tree"
    nested = tree / "src"
    nested.mkdir(parents=True)
    file = nested / "active.py"
    file.write_text("active")
    bh.os.utime(file, (99 * bh.DAY, 99 * bh.DAY))
    bh.os.utime(tree, (1, 1))
    bh.os.utime(nested, (1, 1))
    monkeypatch.setattr(bh, "_now", lambda: 100 * bh.DAY)
    monkeypatch.setattr(bh, "git", lambda *args: "1")
    monkeypatch.setattr(bh, "status_counts", lambda path: (True, False, True))
    row = bh._classify_worktree(_wt(str(tree), branch=None, detached=True), [], 2, 3)
    assert row["action"] == "KEEP"


def test_git_child_drops_inherited_repository_location(monkeypatch):
    observed = {}
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        monkeypatch.setenv(key, "foreign")

    def fake_subprocess(command, **kwargs):
        observed.update(kwargs)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(bh.subprocess, "run", fake_subprocess)
    bh.run(["git", "status"])
    assert all(
        key not in observed["env"]
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")
    )


def test_redirected_quarantine_root_is_rejected(monkeypatch, tmp_path):
    root = tmp_path / "worktrees"
    original = Path.resolve

    def resolve(path, *args, **kwargs):
        return (
            tmp_path.parent / "outside"
            if path == root
            else original(path, *args, **kwargs)
        )

    monkeypatch.setattr(bh, "WT_ROOT", root)
    monkeypatch.setattr(bh, "GOVERNED_WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(Path, "resolve", resolve)
    with pytest.raises(RuntimeError, match="redirected"):
        bh._safe_quarantine_destination(root / "quarantine")


def test_detached_head_is_bundled_before_worktree_removal(monkeypatch, tmp_path):
    calls = _apply_fixture(monkeypatch, tmp_path)
    assert bh.main(["apply", "--out", str(tmp_path), "--execute"]) == 0
    create = next(
        i for i, args in enumerate(calls) if "bundle" in args and "create" in args
    )
    verify = next(
        i for i, args in enumerate(calls) if "bundle" in args and "verify" in args
    )
    remove = next(
        i for i, args in enumerate(calls) if "worktree" in args and "remove" in args
    )
    assert create < verify < remove
    assert calls[create][-1] == "HEAD"


def test_bundle_failure_keeps_completed_actions_journal(monkeypatch, tmp_path):
    import json

    _apply_fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(bh, "_bundle_and_delete", lambda *args: (1, None))
    assert bh.main(["apply", "--out", str(tmp_path), "--execute"]) == 1
    journal = json.loads((tmp_path / "apply-actions.json").read_text())
    assert journal["returncode"] == 1
    assert journal["actions"][0]["remove_rc"] == 0
    assert "bundle failed" in journal["error"]


def test_ignored_local_files_keep_worktree(monkeypatch, tmp_path):
    def run(args, **kwargs):
        return SimpleNamespace(
            returncode=0, stdout="notes.txt\0" if "--ignored" in args else ""
        )

    monkeypatch.setattr(bh, "run", run)
    assert bh.status_counts(tmp_path) is None
    action, _ = bh._worktree_action(
        _wt(str(tmp_path), branch=None, detached=True), [], True, None, 50, 2, 3
    )
    assert action == "KEEP"


def test_open_prs_are_paginated_independently_of_history(monkeypatch):
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(
            returncode=0,
            stdout='[[{"head":{"ref":"old-open"}}]]' if "api" in args else "[]",
        )

    monkeypatch.setattr(bh, "run", run)
    assert bh.pr_state_map() == {"old-open": ["OPEN"]}
    assert "--paginate" in calls[1] and "--slurp" in calls[1]


def test_newly_registered_orphan_is_preserved(monkeypatch, tmp_path):
    tree = tmp_path / "recovered"
    tree.mkdir()
    monkeypatch.setattr(bh, "_safe_tree_target", lambda path: path)
    monkeypatch.setattr(
        bh, "registered_worktrees", lambda: [{"path": str(tree), "locked": "recovery"}]
    )
    monkeypatch.setattr(
        bh.os, "rename", lambda *args: pytest.fail("moved registered worktree")
    )
    result = bh._apply_orphan(
        {
            "path": str(tree),
            "kind": "orphan",
            "action": "QUARANTINE",
            "quarantine": str(tmp_path / "trash"),
        }
    )
    assert result["result"].startswith("kept:") and tree.exists()


def test_branch_delete_is_conditional_on_bundled_sha(monkeypatch):
    import argparse

    candidate = {"name": "stale", "sha": "1" * 40}
    monkeypatch.setattr(bh, "local_branches", lambda: [])
    monkeypatch.setattr(bh, "registered_worktrees", lambda: [])
    monkeypatch.setattr(bh, "git", lambda *args: "HEAD")
    monkeypatch.setattr(
        bh,
        "classify_branches",
        lambda *args: {key: [candidate] if key == "A" else [] for key in "ABCDE"},
    )
    calls = []

    def run(args):
        calls.append(args)
        return SimpleNamespace(returncode=1, stderr="reference changed", stdout="")

    monkeypatch.setattr(bh, "run", run)
    result = bh._delete_one_branch(candidate, argparse.Namespace(branch_days=3))
    assert result["rc"] == 1
    assert calls == [["git", "update-ref", "-d", "refs/heads/stale", candidate["sha"]]]


def test_incomplete_tree_traversal_refuses_mutation(monkeypatch, tmp_path):
    monkeypatch.setattr(bh, "GOVERNED_WORKSPACE_ROOT", tmp_path.parent)

    def scandir(path):
        raise PermissionError("inaccessible subtree")

    monkeypatch.setattr(bh.os, "scandir", scandir)
    with pytest.raises(PermissionError, match="inaccessible"):
        bh._safe_tree_target(tmp_path)
    monkeypatch.setattr(bh, "_now", lambda: 12345)
    assert bh._latest_activity(tmp_path) == 12345


@pytest.mark.parametrize("marker_directory", [False, True])
def test_nested_git_metadata_keeps_quarantine(monkeypatch, tmp_path, marker_directory):
    tree = tmp_path / "old.__trash_20200101"
    nested = tree / "recovery"
    nested.mkdir(parents=True)
    marker = nested / ".git"
    if marker_directory:
        marker.mkdir()
    else:
        marker.write_text("gitdir: preserved-metadata")
    monkeypatch.setattr(bh, "GOVERNED_WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(
        bh.shutil, "rmtree", lambda *args: pytest.fail("deleted nested Git tree")
    )
    result = bh._apply_orphan(
        {"path": str(tree), "kind": "orphan", "action": "HARD_DELETE"}
    )
    assert "nested Git" in result["result"] and marker.exists()


def test_registered_nested_locked_tree_keeps_parent(monkeypatch, tmp_path):
    parent = tmp_path / "parent.__trash_20200101"
    parent.mkdir()
    monkeypatch.setattr(bh, "_safe_tree_target", lambda path: path)
    monkeypatch.setattr(
        bh,
        "registered_worktrees",
        lambda: [{"path": str(parent / "nested"), "locked": "recovery"}],
    )
    monkeypatch.setattr(
        bh.shutil,
        "rmtree",
        lambda *args: pytest.fail("deleted registered nested worktree"),
    )
    result = bh._apply_orphan(
        {"path": str(parent), "kind": "orphan", "action": "HARD_DELETE"}
    )
    assert "registered" in result["result"] and parent.exists()


def test_failed_action_journal_matches_exit_and_prevents_prune(monkeypatch, tmp_path):
    import json

    calls = _apply_fixture(monkeypatch, tmp_path, archive_error=True)
    result = bh.main(["apply", "--out", str(tmp_path), "--execute"])
    journal = json.loads((tmp_path / "apply-actions.json").read_text())
    assert result == journal["returncode"] == 1
    assert journal["error"] and journal["actions"][0]["wip_error"]
    assert not any("prune" in args for args in calls)


@pytest.mark.parametrize("changed,archive_error", [(True, False), (False, True)])
def test_apply_journal_status_matches_failed_actions(
    monkeypatch, tmp_path, changed, archive_error
):
    import json

    _apply_fixture(monkeypatch, tmp_path, changed=changed, archive_error=archive_error)
    rc = bh.main(["apply", "--out", str(tmp_path), "--execute"])
    assert rc == 1
    journals = [
        tmp_path / "apply-actions.json",
        *tmp_path.glob("apply-*/apply-actions.json"),
    ]
    assert len(journals) == 2
    for path in journals:
        journal = json.loads(path.read_text())
        assert journal["returncode"] == rc
        assert journal["error"]
        assert journal["actions"]


def test_renamed_env_source_is_rejected_before_patch_write(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if "--name-only" in args:
            value = (
                ".env.fixture\0ordinary.txt\0"
                if "--no-renames" in args
                else "ordinary.txt\0"
            )
        else:
            value = b"secret context" if kwargs.get("binary") else ""
        return SimpleNamespace(returncode=0, stdout=value)

    monkeypatch.setattr(bh, "run", fake_run)
    with pytest.raises(RuntimeError, match="excluded"):
        bh.archive_tree(tmp_path, "tree", "abc", tmp_path / "archive")
    assert not (tmp_path / "archive").exists()
    assert not any(kwargs for kwargs in calls if "--binary" in kwargs)


@pytest.mark.parametrize("nested", [False, True])
def test_bare_git_metadata_is_preserved(monkeypatch, tmp_path, nested):
    root = tmp_path / "tree"
    bare = root / "nested" if nested else root
    (bare / "objects").mkdir(parents=True)
    (bare / "refs").mkdir()
    (bare / "HEAD").write_text("ref: refs/heads/main\n")
    with pytest.raises(RuntimeError, match="Git"):
        bh._scan_tree_inputs(root)
    assert (bare / "HEAD").exists()


def test_untracked_status_is_independent_of_user_config(monkeypatch, tmp_path):
    def run(args, **kwargs):
        stdout = "?? notes.txt\n" if "--untracked-files=all" in args else ""
        return SimpleNamespace(returncode=0, stdout=stdout)

    monkeypatch.setattr(bh, "run", run)
    assert bh.status_counts(tmp_path) == (False, True, True)


def test_apply_preserves_reviewed_cutoffs(monkeypatch, tmp_path):
    import json

    _apply_fixture(monkeypatch, tmp_path)
    path = tmp_path / "classification.json"
    payload = json.loads(path.read_text())
    payload["cutoffs"] = {"branch_days": 30.0, "detached_days": 20.0}
    path.write_text(json.dumps(payload))
    original = path.read_bytes()
    observed = []

    def classify(args):
        observed.append((args.branch_days, args.detached_days))
        return tmp_path

    monkeypatch.setattr(bh, "_classify_impl", classify)
    assert bh.main(["apply", "--out", str(tmp_path), "--execute"]) == 0
    assert observed == [(30.0, 20.0)]
    assert (
        next(tmp_path.glob("reviewed-*/classification.json")).read_bytes() == original
    )


def test_apply_rejects_changed_cutoffs_before_classification(monkeypatch, tmp_path):
    _apply_fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(
        bh, "_classify_impl", lambda args: pytest.fail("unexpected classification")
    )
    with pytest.raises(RuntimeError, match="Cutoffs changed"):
        bh.main(["apply", "--out", str(tmp_path), "--execute", "--branch-days", "30"])


def test_partial_branch_failure_retains_bundle_in_journal(monkeypatch, tmp_path):
    import json

    _apply_fixture(monkeypatch, tmp_path)
    path = tmp_path / "classification.json"
    payload = json.loads(path.read_text())
    payload["branches"]["A"] = [{"name": "one"}, {"name": "two"}]
    path.write_text(json.dumps(payload))

    def delete(item, args):
        if item["name"] == "two":
            raise RuntimeError("PR lookup unavailable")
        return {"kind": "branch", "name": "one", "rc": 0}

    monkeypatch.setattr(bh, "_delete_one_branch", delete)
    assert bh.main(["apply", "--out", str(tmp_path), "--execute"]) == 1
    journal = json.loads((tmp_path / "apply-actions.json").read_text())
    assert journal["bundle"].endswith("history.bundle")
    assert journal["actions"][-1]["name"] == "one"
    assert "PR lookup" in journal["error"]


def test_apply_does_not_add_unreviewed_candidates(monkeypatch, tmp_path):
    import json

    _apply_fixture(monkeypatch, tmp_path)
    path = tmp_path / "classification.json"
    reviewed = json.loads(path.read_text())
    reviewed["worktrees"] = []
    path.write_text(json.dumps(reviewed))

    def refresh(args):
        fresh = {
            **reviewed,
            "orphans": [{"path": "new-unreviewed", "action": "HARD_DELETE"}],
        }
        path.write_text(json.dumps(fresh))
        return tmp_path

    monkeypatch.setattr(bh, "_classify_impl", refresh)
    monkeypatch.setattr(
        bh, "_apply_orphan", lambda row: pytest.fail("unreviewed target")
    )
    assert bh.main(["apply", "--out", str(tmp_path), "--execute"]) == 0
