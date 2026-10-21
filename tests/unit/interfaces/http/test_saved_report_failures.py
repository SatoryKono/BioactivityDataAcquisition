"""HTTP report evidence distinguishes absence from corrupt or unreadable data."""

from datetime import datetime
from pathlib import Path

import pytest

from bioetl.interfaces.http._identity_display_rows import format_timestamp_label
from bioetl.interfaces.http.recent_pipeline_runs import _format_compact_duration
from bioetl.interfaces.http.run_report_ops import (
    InvalidRunReportError,
    _load_workflow_payload,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "raw, reason", [(b"\xff", "malformed_encoding"), (b"[]", "invalid_payload")]
)
def test_corrupt_workflow_report_is_never_treated_as_missing(tmp_path, raw, reason):
    path = tmp_path / "workflow-run-report.json"
    path.write_bytes(raw)
    with pytest.raises(InvalidRunReportError) as caught:
        _load_workflow_payload(path)
    assert caught.value.reason == reason


def test_unreadable_workflow_report_preserves_failure_reason(tmp_path, monkeypatch):
    path = tmp_path / "workflow-run-report.json"
    path.write_text("{}", encoding="utf-8")

    def denied(*args, **kwargs):
        raise PermissionError("report is unreadable")

    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(InvalidRunReportError) as caught:
        _load_workflow_payload(path)
    assert caught.value.reason == "report_read_error"
    assert isinstance(caught.value.__cause__, PermissionError)


def test_compact_duration_carries_rounded_hour():
    assert _format_compact_duration(7199) == "2 h"


def test_naive_saved_timestamp_has_explicit_utc_interpretation():
    assert (
        format_timestamp_label(datetime(2026, 10, 21, 12, 30), "UTC")
        == "2026-10-21 12:30 UTC"
    )
