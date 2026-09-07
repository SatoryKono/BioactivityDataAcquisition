"""Unit tests for FileRunReportStoreAdapter (#9084)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.ports.storage.run_report_store import RunReportStorePort
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)

pytestmark = pytest.mark.unit


def test_adapter_satisfies_port_and_round_trips_text(tmp_path: Path) -> None:
    adapter = FileRunReportStoreAdapter()
    assert isinstance(adapter, RunReportStorePort)
    target = tmp_path / "nested" / "report.json"
    adapter.mkdir(str(target.parent))
    payload = '{"ok": true}' + chr(10)
    adapter.write_text(str(target), payload)
    assert adapter.read_text(str(target)) == payload


@pytest.mark.parametrize("suffix", [".", "..", "nested/../.."])
def test_remove_tree_rejects_root_and_parent_traversal(
    tmp_path: Path, suffix: str
) -> None:
    root = tmp_path / "reports"
    root.mkdir()
    outside = tmp_path / "keep.txt"
    outside.write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError):
        FileRunReportStoreAdapter().remove_tree(str(root / suffix), root=str(root))
    assert root.is_dir()
    assert outside.read_text(encoding="utf-8") == "keep"


def test_remove_tree_deletes_only_report_directory(tmp_path: Path) -> None:
    report = tmp_path / "pipeline" / "owner" / "run"
    report.mkdir(parents=True)
    (report / "report.json").write_text("{}", encoding="utf-8")
    FileRunReportStoreAdapter().remove_tree(str(report), root=str(tmp_path))
    assert not report.exists()
    assert report.parent.is_dir()


def _require_symlink_privilege(tmp_path: Path) -> None:
    probe = tmp_path / "_symlink_probe_src"
    probe.write_text("x", encoding="utf-8")
    try:
        (tmp_path / "_symlink_probe").symlink_to(probe)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege is not granted")
        raise


def test_report_tree_removal_unlinks_symlink(tmp_path: Path) -> None:
    _require_symlink_privilege(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)

    FileRunReportStoreAdapter().remove_tree(str(link), root=str(tmp_path))

    assert not link.exists()
    assert target.is_dir()
