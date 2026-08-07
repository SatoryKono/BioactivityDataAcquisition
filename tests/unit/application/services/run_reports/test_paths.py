# pyright: reportArgumentType=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict.
"""Unit tests for report-root path resolution and bind marker."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.application.services.run_reports import paths as run_report_paths

pytestmark = pytest.mark.unit

from bioetl.application.services.run_reports.paths import (
    REPORT_ROOT_MARKER_NAME,
    REPORT_ROOT_MARKER_VALUE,
    inspect_report_root_marker,
    report_root_marker_is_healthy,
    report_root_marker_path,
    resolve_report_root,
)


def test_resolve_report_root_default() -> None:
    assert resolve_report_root() == run_report_paths.DEFAULT_REPORT_ROOT
    assert resolve_report_root(root=None) == run_report_paths.DEFAULT_REPORT_ROOT


def test_resolve_report_root_explicit(tmp_path: Path) -> None:
    assert resolve_report_root(root=tmp_path) == tmp_path
    assert resolve_report_root(root=tmp_path / "custom") == tmp_path / "custom"


def test_marker_path_for_default_layout() -> None:
    marker = report_root_marker_path(report_root=Path("reports") / "run-reports")
    assert marker == Path("reports") / REPORT_ROOT_MARKER_NAME


def test_marker_path_for_container_layout() -> None:
    marker = report_root_marker_path(report_root=Path("/app/reports/run-reports"))
    assert marker == Path("/app/reports") / REPORT_ROOT_MARKER_NAME


def test_marker_path_for_isolated_test_root(tmp_path: Path) -> None:
    # Isolated roots are not named run-reports — marker lives under the root.
    assert report_root_marker_path(report_root=tmp_path) == (
        tmp_path / REPORT_ROOT_MARKER_NAME
    )


def test_inspect_marker_missing(tmp_path: Path) -> None:
    root = tmp_path / "run-reports"
    root.mkdir()
    check = inspect_report_root_marker(report_root=root)
    assert check["status"] == "unhealthy"
    assert check["marker"] == "missing"
    assert not report_root_marker_is_healthy(report_root=root)


def test_inspect_marker_ok(tmp_path: Path) -> None:
    root = tmp_path / "run-reports"
    root.mkdir()
    marker = tmp_path / REPORT_ROOT_MARKER_NAME
    marker.write_text(REPORT_ROOT_MARKER_VALUE + "\n", encoding="utf-8")
    check = inspect_report_root_marker(report_root=root)
    assert check["status"] == "healthy"
    assert check["marker"] == "ok"
    assert report_root_marker_is_healthy(report_root=root)


def test_inspect_marker_token_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "run-reports"
    root.mkdir()
    (tmp_path / REPORT_ROOT_MARKER_NAME).write_text("wrong\n", encoding="utf-8")
    check = inspect_report_root_marker(report_root=root)
    assert check["status"] == "unhealthy"
    assert check["marker"] == "mismatch"
