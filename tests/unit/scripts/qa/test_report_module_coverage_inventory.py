# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.engineering.qa.report_module_coverage_inventory import (
    _SourceModuleSnapshot,
    _module_is_declaration_only,
    _read_source_module_snapshots,
    _read_stable_source_module_snapshots,
    _refresh_existing_inventory_source_tree,
)

pytestmark = pytest.mark.unit


def test_read_source_module_snapshots_skips_vanished_path(
    tmp_path: Path,
) -> None:
    present = tmp_path / "present.py"
    vanished = tmp_path / "vanished.py"
    present.write_text("x = 1\n", encoding="utf-8")
    vanished.write_text("y = 2\n", encoding="utf-8")
    vanished.unlink()

    snapshots, digest = _read_source_module_snapshots(
        [present, vanished],
        tmp_path,
    )

    assert digest
    assert [snapshot.repo_path for snapshot in snapshots] == ["present.py"]


def test_read_stable_source_module_snapshots_retries_until_digest_stabilizes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    present = tmp_path / "present.py"
    present.write_text("x = 1\n", encoding="utf-8")

    calls = iter(
        [
            ([SimpleNamespace(repo_path="present.py")], "digest-a"),
            ([SimpleNamespace(repo_path="present.py")], "digest-b"),
            ([SimpleNamespace(repo_path="present.py")], "digest-b"),
        ]
    )

    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory._iter_source_modules",
        lambda repo_root: [present],
    )
    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory._read_source_module_snapshots",
        lambda source_paths, repo_root: next(calls),
    )

    snapshots, digest = _read_stable_source_module_snapshots(tmp_path, max_attempts=3)

    assert [snapshot.repo_path for snapshot in snapshots] == ["present.py"]
    assert digest == "digest-b"


def test_refresh_existing_inventory_reuses_stable_snapshot_digest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "src" / "bioetl" / "present.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("x = 1\n", encoding="utf-8")
    snapshot = _SourceModuleSnapshot(
        path=source_path,
        repo_path="src/bioetl/present.py",
        source_lines=1,
        declaration_only=False,
    )

    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory._read_stable_source_module_snapshots",
        lambda repo_root: ([snapshot], "stable-digest"),
    )
    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory._build_hotspot_family_coverage",
        lambda rows, *, repo_root: {},
    )
    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory.compute_source_tree_sha256",
        lambda *, repo_root: pytest.fail(
            "source hash should come from stable snapshot read"
        ),
    )

    refreshed = _refresh_existing_inventory_source_tree(
        {
            "modules": [
                {
                    "module": "bioetl.present",
                    "path": "src/bioetl/present.py",
                    "source_lines": 999,
                    "coverage_status": "fully_covered",
                    "coverage_percent": 100.0,
                    "executable_lines": 1,
                    "covered_lines": 1,
                    "missing_lines": 0,
                }
            ],
            "summary": {"source_tree_sha256": "stale-summary-digest"},
            "source_tree_sha256": "old-digest",
        },
        repo_root=tmp_path,
    )

    assert refreshed["source_tree_sha256"] == "stable-digest"
    assert refreshed["modules"][0]["source_lines"] == 999
    assert refreshed["summary"] == {
        "source_tree_sha256": "stale-summary-digest"
    }


def test_module_is_declaration_only_treats_private_attrs_surface_as_non_runtime() -> (
    None
):
    source = (
        '"""Typed attrs."""\n'
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from x import Y\n"
        "class _Attrs:\n"
        "    __slots__ = ('a',)\n"
        "    a: int\n"
        "__all__ = ['_Attrs']\n"
    )

    assert _module_is_declaration_only(source) is True


def test_module_is_declaration_only_rejects_runtime_behavior() -> None:
    source = "def build() -> int:\n    return 1\n"

    assert _module_is_declaration_only(source) is False
