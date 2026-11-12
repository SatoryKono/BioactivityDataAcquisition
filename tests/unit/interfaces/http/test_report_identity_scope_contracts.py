"""Cached verified report identities retain scope, uniqueness and honest time."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import pytest
from bioetl.application.services.run_reports.query import ReportIndexEntry
from bioetl.interfaces.http import _report_selector_options as subject

pytestmark = pytest.mark.unit


def entry(tmp_path):
    identity = {
        "run_id": "run-a",
        "pipeline_name": "chembl_activity",
        "workflow_id": "other",
        "started_at": "2026-01-02T03:04:05",
    }
    return ReportIndexEntry(
        kind="pipeline",
        owner="chembl_activity",
        run_id="run-a",
        json_path=tmp_path / "unused.json",
        markdown_path=None,
        status="success",
        started_at=None,
        completed_at=None,
        mtime=0,
        identity_snapshot=identity,
        schema_version="pipeline_run_report_v1",
    )


def test_verified_identity_outside_workflow_scope_is_excluded(tmp_path):
    assert (
        subject._iter_verified_report_identities(
            {"workflow": ("wanted",)}, root=tmp_path, entries=[entry(tmp_path)]
        )
        == ()
    )


def test_duplicate_verified_run_is_emitted_once_and_naive_time_is_utc(tmp_path):
    item = entry(tmp_path)
    rows = subject._iter_verified_report_identities(
        {}, root=tmp_path, entries=[item, item]
    )
    assert len(rows) == 1
    assert rows[0][0] == "run-a"
    assert rows[0][1] == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_invalid_timestamp_does_not_discard_verified_identity_or_invent_time(tmp_path):
    item = entry(tmp_path)
    item = replace(
        item, identity_snapshot={**item.identity_snapshot, "started_at": "invalid"}
    )
    rows = subject._iter_verified_report_identities({}, root=tmp_path, entries=[item])
    assert len(rows) == 1
    assert rows[0][0] == "run-a"
    assert rows[0][1] is None
