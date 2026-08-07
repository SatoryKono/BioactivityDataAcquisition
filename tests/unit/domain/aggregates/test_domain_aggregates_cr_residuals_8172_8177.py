# pyright: reportArgumentType=false
"""Residual closeout coverage for domain/aggregates CR-FULL #8172-#8177."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bioetl.domain.aggregates.batch import Batch
from bioetl.domain.aggregates.pipeline_run import StageResult, StageStatus
from bioetl.domain.aggregates.quarantine_entry import (
    QuarantineEntry,
    QuarantineStatus,
    ResolutionInfo,
)
from bioetl.domain.aggregates._batch_lifecycle import emit_record_quarantined
from bioetl.domain.types import BatchID, EntityID, RunID
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = pytest.mark.unit


def _ts(offset_seconds: int = 0) -> datetime:
    return datetime(2024, 1, 1, tzinfo=UTC) + timedelta(seconds=offset_seconds)


def _run_id(label: str = "unit.aggregates.residuals.run") -> RunID:
    return RunID(deterministic_uuid_value(label))


def _batch_id(label: str = "unit.aggregates.residuals.batch") -> BatchID:
    return BatchID(deterministic_uuid_value(label))


def test_stage_result_rejects_completed_at_while_pending_or_running() -> None:
    started = _ts(0)
    for status in (StageStatus.PENDING, StageStatus.RUNNING):
        with pytest.raises(ValueError, match="must not have completed_at"):
            StageResult(
                stage="preflight",
                status=status,
                started_at=started,
                completed_at=_ts(1),
            )


def test_stage_result_rejects_completed_at_before_started_at() -> None:
    with pytest.raises(ValueError, match="cannot be earlier than started_at"):
        StageResult(
            stage="preflight",
            status=StageStatus.SUCCESS,
            started_at=_ts(10),
            completed_at=_ts(5),
        )


def test_stage_result_duration_only_for_completed_stages() -> None:
    started = _ts(0)
    running = StageResult(
        stage="preflight",
        status=StageStatus.RUNNING,
        started_at=started,
        completed_at=None,
    )
    assert running.duration_seconds is None

    done = StageResult(
        stage="preflight",
        status=StageStatus.SUCCESS,
        started_at=started,
        completed_at=_ts(5),
    )
    assert done.duration_seconds == pytest.approx(5.0)


def test_emit_record_quarantined_preserves_empty_entity_id() -> None:
    events: list = []
    emit_record_quarantined(
        events,
        _run_id(),
        _batch_id(),
        EntityID(""),
        "ERR",
        "boom",
        None,
        _ts(1),
    )
    assert events[0].record_id == ""


def test_seal_with_counts_rejects_negative_and_inconsistent_counts() -> None:
    batch = Batch.create(
        run_id=_run_id("unit.aggregates.residuals.seal"), created_at=_ts(0)
    )
    with pytest.raises(ValueError, match="non-negative"):
        batch.seal_with_counts(
            record_count=-1,
            valid_count=0,
            quarantined_count=0,
            sealed_at=_ts(1),
        )
    with pytest.raises(ValueError, match="inconsistent"):
        batch.seal_with_counts(
            record_count=3,
            valid_count=1,
            quarantined_count=1,
            sealed_at=_ts(1),
        )


def test_quarantine_record_uses_batch_record_index_offset() -> None:
    batch = Batch.create(
        run_id=_run_id("unit.aggregates.residuals.qpos"),
        start_index=10,
        created_at=_ts(0),
    )
    first = batch.add_record({"id": "a"})
    second = batch.add_record({"id": "b"})
    assert first.index == 10
    assert second.index == 11
    quarantined = batch.quarantine_record(second, "bad", "ERR", quarantined_at=_ts(2))
    assert quarantined.index == 11
    assert batch.all_records[1].is_valid is False
    assert batch.quarantined_count == 1


def test_resolution_info_allowed_types_come_from_quarantine_status() -> None:
    resolved_at = _ts(3)
    for status in QuarantineStatus:
        if not status.is_terminal():
            continue
        info = ResolutionInfo(resolution_type=status.value, resolved_at=resolved_at)
        assert info.resolution_type == status.value
    with pytest.raises(ValueError, match="Invalid resolution_type"):
        ResolutionInfo(resolution_type="unknown", resolved_at=resolved_at)


def test_quarantine_entry_create_and_resolve_use_explicit_timestamps() -> None:
    created_at = _ts(0)
    resolved_at = _ts(5)
    entry = QuarantineEntry.create(
        pipeline_name="chembl_activity",
        error_code="SCHEMA_VIOLATION",
        payload={"id": "bad-record"},
        run_id=_run_id("unit.aggregates.residuals.qe"),
        batch_id=_batch_id("unit.aggregates.residuals.qe.batch"),
        created_at=created_at,
    )
    entry.start_review()
    entry.mark_ignored(reason="Known bad data source", resolved_at=resolved_at)
    assert entry.status == QuarantineStatus.IGNORED
    assert entry.resolution_info is not None
    assert entry.resolution_info.resolved_at == resolved_at
    assert entry.created_at == created_at
