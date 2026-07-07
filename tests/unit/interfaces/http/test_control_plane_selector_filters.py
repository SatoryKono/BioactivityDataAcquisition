"""Focused tests for control-plane selector filtering helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from bioetl.interfaces.http import _control_plane_selector_filters as subject
from bioetl.interfaces.http._control_plane_selector_records import SelectorRecord

pytestmark = pytest.mark.unit


def _record(
    suffix: str,
    *,
    workflow_candidates: tuple[str, ...],
    pipeline: str,
    run_type: str,
    run_status: str,
    completed_offset: int,
) -> SelectorRecord:
    return SelectorRecord(
        manifest=cast(Any, None),
        workflow=workflow_candidates[0],
        workflow_candidates=workflow_candidates,
        pipeline=pipeline,
        run_type=run_type,
        run_id=f"run-{suffix}",
        provider=pipeline.split("_", 1)[0],
        entity=pipeline.split("_", 1)[-1],
        manifest_id=f"manifest-{suffix}",
        completed_at=datetime(2026, 7, 7, 9, 0, tzinfo=UTC)
        + timedelta(minutes=completed_offset),
        completed_at_source="test",
        run_status=run_status,
        terminal_event_type=None,
    )


def test_filter_records_honors_exact_run_id_before_other_dimensions() -> None:
    first = _record(
        "1",
        workflow_candidates=("wf-a",),
        pipeline="chembl_activity",
        run_type="incremental",
        run_status="success",
        completed_offset=1,
    )
    second = _record(
        "2",
        workflow_candidates=("wf-b",),
        pipeline="pubchem_compound",
        run_type="backfill",
        run_status="failed",
        completed_offset=2,
    )

    assert subject.filter_records(
        (first, second),
        selected_workflows=("wf-a",),
        selected_pipelines=("chembl_activity",),
        selected_run_types=("incremental",),
        selected_run_statuses=("success",),
        selected_run_id="run-2",
    ) == (second,)


def test_filter_records_requires_all_selected_dimensions_to_match() -> None:
    first = _record(
        "1",
        workflow_candidates=("wf-a", "wf-shared"),
        pipeline="chembl_activity",
        run_type="incremental",
        run_status="success",
        completed_offset=1,
    )
    second = _record(
        "2",
        workflow_candidates=("wf-b", "wf-shared"),
        pipeline="chembl_target",
        run_type="incremental",
        run_status="success",
        completed_offset=2,
    )
    third = _record(
        "3",
        workflow_candidates=("wf-c",),
        pipeline="chembl_activity",
        run_type="backfill",
        run_status="success",
        completed_offset=3,
    )

    assert subject.filter_records(
        (first, second, third),
        selected_workflows=("wf-shared",),
        selected_pipelines=("chembl_activity",),
        selected_run_types=("incremental",),
        selected_run_statuses=("success",),
        selected_run_id=None,
    ) == (first,)


def test_latest_record_uses_completed_at_then_manifest_id_tie_breaker() -> None:
    older = _record(
        "a",
        workflow_candidates=("wf-a",),
        pipeline="chembl_activity",
        run_type="incremental",
        run_status="success",
        completed_offset=1,
    )
    same_time_lower_manifest = _record(
        "b",
        workflow_candidates=("wf-a",),
        pipeline="chembl_activity",
        run_type="incremental",
        run_status="success",
        completed_offset=2,
    )
    same_time_higher_manifest = _record(
        "c",
        workflow_candidates=("wf-a",),
        pipeline="chembl_activity",
        run_type="incremental",
        run_status="success",
        completed_offset=2,
    )

    assert subject.latest_record(()) is None
    assert (
        subject.latest_record(
            (older, same_time_lower_manifest, same_time_higher_manifest)
        )
        is same_time_higher_manifest
    )
