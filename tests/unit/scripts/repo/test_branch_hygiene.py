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
