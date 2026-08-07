# pyright: reportArgumentType=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict.
"""Unit tests for interfaces report-root env bridge and readiness check."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from bioetl.application.services.run_reports.paths import (
    REPORT_ROOT_MARKER_NAME,
    REPORT_ROOT_MARKER_VALUE,
)
from bioetl.interfaces.http.report_root_config import (
    ENFORCE_REPORT_ROOT_MARKER_ENV,
    REPORT_ROOT_ENV,
    configured_report_root,
    enforce_report_root_marker,
    report_root_readiness_check,
)


def test_configured_report_root_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(REPORT_ROOT_ENV, str(tmp_path / "run-reports"))
    assert configured_report_root() == tmp_path / "run-reports"


def test_configured_report_root_explicit_wins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(REPORT_ROOT_ENV, str(tmp_path / "env-root"))
    explicit = tmp_path / "explicit"
    assert configured_report_root(root=explicit) == explicit


def test_enforce_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENFORCE_REPORT_ROOT_MARKER_ENV, raising=False)
    assert enforce_report_root_marker() is False
    monkeypatch.setenv(ENFORCE_REPORT_ROOT_MARKER_ENV, "1")
    assert enforce_report_root_marker() is True
    monkeypatch.setenv(ENFORCE_REPORT_ROOT_MARKER_ENV, "true")
    assert enforce_report_root_marker() is True
    monkeypatch.setenv(ENFORCE_REPORT_ROOT_MARKER_ENV, "0")
    assert enforce_report_root_marker() is False


def test_readiness_check_with_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "run-reports"
    root.mkdir()
    (tmp_path / REPORT_ROOT_MARKER_NAME).write_text(
        REPORT_ROOT_MARKER_VALUE + "\n", encoding="utf-8"
    )
    monkeypatch.setenv(REPORT_ROOT_ENV, str(root))
    monkeypatch.setenv(ENFORCE_REPORT_ROOT_MARKER_ENV, "1")
    check = report_root_readiness_check()
    assert check["status"] == "healthy"
    assert check["enforced"] is True
    assert check["env_set"] is True


def test_readiness_check_missing_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "run-reports"
    root.mkdir()
    monkeypatch.setenv(REPORT_ROOT_ENV, str(root))
    check = report_root_readiness_check()
    assert check["status"] == "unhealthy"
    assert check["marker"] == "missing"
