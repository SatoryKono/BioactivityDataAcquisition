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
    REPORT_ROOT_SOURCE_IDENTITY_NAME,
    REPORT_ROOT_SOURCE_IDENTITY_SCHEMA,
    inspect_report_root_marker,
    inspect_report_root_source_identity,
    report_root_marker_is_healthy,
    report_root_marker_path,
    report_root_source_identity_path,
    resolve_report_root,
    write_report_root_source_identity,
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


def test_inspect_marker_bounds_reads_and_handles_invalid_encoding(tmp_path: Path) -> None:
    root = tmp_path / "run-reports"
    root.mkdir()
    marker = tmp_path / REPORT_ROOT_MARKER_NAME
    marker.write_bytes(b"\xff\xfe")

    invalid = inspect_report_root_marker(report_root=root)

    assert invalid["status"] == "unhealthy"
    assert invalid["marker"] == "unreadable"

    marker.write_text(REPORT_ROOT_MARKER_VALUE + (" " * 5000), encoding="utf-8")
    oversized = inspect_report_root_marker(report_root=root)
    assert oversized["status"] == "unhealthy"
    assert oversized["marker"] == "mismatch"


def test_source_identity_temp_file_is_cleaned_when_fsync_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "run-reports"
    root.mkdir()

    def _fail_fsync(_file_descriptor: int) -> None:
        raise OSError("fsync failed")

    monkeypatch.setattr(run_report_paths.os, "fsync", _fail_fsync)

    with pytest.raises(OSError, match="fsync failed"):
        write_report_root_source_identity(report_root=root, source_id="a" * 64)

    assert list(tmp_path.glob(f"{REPORT_ROOT_SOURCE_IDENTITY_NAME}.*.tmp")) == []


def test_source_identity_path_follows_bind_root_layout(tmp_path: Path) -> None:
    root = tmp_path / "run-reports"
    assert report_root_source_identity_path(report_root=root) == (
        tmp_path / REPORT_ROOT_SOURCE_IDENTITY_NAME
    )


def test_source_identity_round_trip_exact_match(tmp_path: Path) -> None:
    root = tmp_path / "run-reports"
    root.mkdir()
    source_id = "a" * 64

    target = write_report_root_source_identity(
        report_root=root,
        source_id=source_id,
    )
    check = inspect_report_root_source_identity(
        report_root=root,
        expected_source_id=source_id,
    )

    assert target.name == REPORT_ROOT_SOURCE_IDENTITY_NAME
    assert check["source_identity_status"] == "healthy"
    assert check["source_identity"] == "ok"
    assert check["source_identity_state"] == "aligned"
    assert check["source_identity_schema_actual"] == REPORT_ROOT_SOURCE_IDENTITY_SCHEMA
    assert check["source_identity_actual"] == source_id


def test_source_identity_fails_closed_for_foreign_checkout(tmp_path: Path) -> None:
    root = tmp_path / "run-reports"
    root.mkdir()
    write_report_root_source_identity(report_root=root, source_id="a" * 64)

    check = inspect_report_root_source_identity(
        report_root=root,
        expected_source_id="b" * 64,
    )

    assert check["source_identity_status"] == "unhealthy"
    assert check["source_identity"] == "mismatch"
    assert check["source_identity_state"] == "foreign"
    assert check["source_identity_actual"] == "a" * 64


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        (None, "missing"),
        ("not-json", "unreadable"),
        (
            '{"schema_version":"wrong","runtime_source_id":"' + "a" * 64 + '"}',
            "schema_mismatch",
        ),
        (
            '{"schema_version":"bioetl-report-source-v1","runtime_source_id":"bad"}',
            "invalid",
        ),
    ],
)
def test_source_identity_invalid_states_fail_closed(
    tmp_path: Path,
    payload: str | None,
    reason: str,
) -> None:
    root = tmp_path / "run-reports"
    root.mkdir()
    marker = tmp_path / REPORT_ROOT_SOURCE_IDENTITY_NAME
    if payload is not None:
        marker.write_text(payload, encoding="utf-8")

    check = inspect_report_root_source_identity(
        report_root=root,
        expected_source_id="a" * 64,
    )

    assert check["source_identity_status"] == "unhealthy"
    assert check["source_identity"] == reason
    assert check["source_identity_state"] == (
        "missing" if reason == "missing" else "invalid"
    )
