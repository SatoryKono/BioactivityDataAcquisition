"""Unit tests for branch_hygiene classification helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.engineering.repo import branch_hygiene as bh

pytestmark = pytest.mark.unit


def _stub_os(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bh, "os", SimpleNamespace(stat=lambda p, **kw: SimpleNamespace(st_mtime=0))
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
    def fake_run(args):
        output = "?? newdir/.env.production\n" if "status" in args else ""
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
                "worktrees": [row],
                "orphans": [],
                "branches": {key: [] for key in "ABCDE"},
            }
        )
    )
    monkeypatch.setattr(bh, "_classify_impl", lambda args: tmp_path)
    monkeypatch.setattr(bh, "registered_worktrees", lambda: [])
    monkeypatch.setattr(bh, "local_branches", lambda: [])
    monkeypatch.setattr(
        bh,
        "classify_worktrees",
        lambda *args: [{**row, "head": "new"}] if changed else [row],
    )
    monkeypatch.setattr(bh, "_safe_tree_target", lambda path: path)

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
    assert bh.main(["apply", "--out", str(tmp_path), "--execute"]) == int(archive_error)
    assert not any("remove" in args for args in calls)


def test_tree_guard_rejects_nested_env_without_creating_env(monkeypatch, tmp_path):
    monkeypatch.setattr(
        bh.os,
        "walk",
        lambda *args, **kwargs: [(str(tmp_path), [], [".env.production"])],
    )
    with pytest.raises(RuntimeError, match="env or linked"):
        bh._safe_tree_target(tmp_path)


def test_worktree_removal_uses_git_dirty_protection(monkeypatch, tmp_path):
    calls = _apply_fixture(monkeypatch, tmp_path)
    assert bh.main(["apply", "--out", str(tmp_path), "--execute"]) == 0
    removals = [args for args in calls if "remove" in args]
    assert len(removals) == 1
    assert "--force" not in removals[0]


@pytest.mark.parametrize("target", ["D:/", "D:/github"])
def test_tree_guard_refuses_drive_or_governed_root(target):
    with pytest.raises(RuntimeError, match="outside governed workspace"):
        bh._safe_tree_target(bh.Path(target))


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
    monkeypatch.setattr(bh, "WT_ROOT", root)
    bh._safe_quarantine_destination(root / ".__trash_20261113" / "retained")
    with pytest.raises(RuntimeError, match="escapes"):
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
