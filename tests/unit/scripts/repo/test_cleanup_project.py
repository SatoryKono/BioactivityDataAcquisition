"""Unit tests for deterministic local artifact cleanup."""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.diagnostics import cleanup_project as module


def test_find_cleanup_targets_skips_blocked_cleanup_zones(tmp_path: Path) -> None:
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / "reports" / ".pytest_cache").mkdir(parents=True)
    (tmp_path / "docs" / "reports" / "trace.log").parent.mkdir(parents=True)
    (tmp_path / "docs" / "reports" / "trace.log").write_text("log", encoding="utf-8")

    targets = module.find_cleanup_targets(
        tmp_path,
        include_logs=True,
        blocked_cleanup_paths=frozenset({"reports", "docs/reports"}),
    )
    rel_paths = {
        target.path.relative_to(tmp_path).as_posix()
        for target in targets
    }

    assert ".pytest_cache" in rel_paths
    assert "reports/.pytest_cache" not in rel_paths
    assert "docs/reports/trace.log" not in rel_paths


def test_archive_logs_uses_deterministic_default_directory(tmp_path: Path) -> None:
    log_path = tmp_path / "worker.log"
    log_path.write_text("hello", encoding="utf-8")
    target = module.CleanupTarget(
        path=log_path,
        category="log",
        size_bytes=5,
        is_dir=False,
    )

    archived = module.archive_logs(tmp_path, [target])

    assert archived == [target]
    assert (
        tmp_path / "reports" / "archived_logs" / "manual" / "worker.log"
    ).exists()
