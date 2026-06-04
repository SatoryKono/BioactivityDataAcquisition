from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.engineering.qa.report_module_coverage_inventory import (
    _read_source_module_snapshots,
    _read_stable_source_module_snapshots,
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

    snapshots, digest = _read_stable_source_module_snapshots(tmp_path, max_attempts=4)

    assert [snapshot.repo_path for snapshot in snapshots] == ["present.py"]
    assert digest == "digest-b"
