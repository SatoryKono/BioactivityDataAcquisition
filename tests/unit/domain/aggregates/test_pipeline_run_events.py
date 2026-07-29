# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Tests for PipelineRun domain event payloads and serialization contracts."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

import pytest

from bioetl.domain.aggregates.pipeline_run import PipelineRun, PipelineRunState
from bioetl.domain.aggregates.events import (
    BatchCreated,
    PipelineCompleted,
    PipelineFailed,
    PipelineShutdown,
)
from bioetl.domain.types import RunID, RunType
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = pytest.mark.unit


def _ts(minutes: int = 0, seconds: int = 0) -> datetime:
    """Return deterministic UTC timestamp."""
    return datetime(2026, 1, 1, 12, minutes, seconds, tzinfo=UTC)


def _run(run_id: RunID) -> PipelineRun:
    return PipelineRun(
        run_id=run_id, run_type=RunType.INCREMENTAL, pipeline_name="test_pipeline"
    )


def _run_id() -> RunID:
    return RunID(deterministic_uuid_value("unit.pipeline_run_events"))


def test_pipeline_completed_event_payload_roundtrip() -> None:
    """Completed event payload should be deterministic and round-trippable."""
    pipeline_run = _run(_run_id())
    pipeline_run.start(_ts(0))
    pipeline_run.record_stage_success(
        "test",
        records_processed=120,
        started_at=_ts(0, 0),
        completed_at=_ts(0, 10),
    )
    pipeline_run.complete(_ts(0, 20))

    events = pipeline_run.collect_events()
    assert pipeline_run.status == PipelineRunState.COMPLETED
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, PipelineCompleted)
    assert event.duration_seconds == 20.0

    payload = asdict(event)
    assert payload["run_id"] == pipeline_run.run_id
    assert payload["pipeline_name"] == pipeline_run.pipeline_name
    assert payload["records_processed"] == 120
    assert payload["stages_count"] == 1

    reconstructed = PipelineCompleted(
        occurred_at=payload["occurred_at"],
        run_id=payload["run_id"],
        pipeline_name=payload["pipeline_name"],
        records_processed=payload["records_processed"],
        duration_seconds=payload["duration_seconds"],
        stages_count=payload["stages_count"],
    )
    assert reconstructed == event
    assert reconstructed.event_id == event.event_id


def test_pipeline_failed_event_payload_roundtrip() -> None:
    """Failed event payload should preserve all failure details."""
    pipeline_run = _run(_run_id())
    pipeline_run.start(_ts(0))
    pipeline_run.record_stage_failure(
        "extract",
        "pipeline exploded",
        error_type="RuntimeError",
        started_at=_ts(0, 5),
        completed_at=_ts(0, 10),
    )

    events = pipeline_run.collect_events()
    assert pipeline_run.status == PipelineRunState.FAILED
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, PipelineFailed)
    assert event.failed_stage == "extract"
    assert event.error_type == "RuntimeError"

    payload = asdict(event)
    reconstructed = PipelineFailed(
        occurred_at=payload["occurred_at"],
        run_id=payload["run_id"],
        pipeline_name=payload["pipeline_name"],
        failed_stage=payload["failed_stage"],
        error=payload["error"],
        error_type=payload["error_type"],
    )
    assert reconstructed == event
    assert reconstructed.event_id == event.event_id


def test_pipeline_shutdown_event_payload_roundtrip() -> None:
    """Shutdown event payload should preserve records_processed and pipeline identity."""
    pipeline_run = _run(_run_id())
    pipeline_run.start(_ts(0))
    pipeline_run.record_stage_success(
        "test",
        records_processed=10,
        started_at=_ts(0, 0),
        completed_at=_ts(0, 3),
    )
    pipeline_run.shutdown(_ts(0, 8))

    events = pipeline_run.collect_events()
    assert pipeline_run.status == PipelineRunState.SHUTDOWN
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, PipelineShutdown)
    assert event.records_processed == 10

    payload = asdict(event)
    assert payload["run_id"] == pipeline_run.run_id

    reconstructed = PipelineShutdown(
        occurred_at=payload["occurred_at"],
        run_id=payload["run_id"],
        pipeline_name=payload["pipeline_name"],
        records_processed=payload["records_processed"],
    )
    assert reconstructed == event
    assert reconstructed.event_id == event.event_id


def test_domain_event_preserves_explicit_event_id() -> None:
    """DomainEvent should not overwrite a caller-supplied event_id."""
    run_id = _run_id()
    explicit_id = "fixed-event-id"
    event = BatchCreated(
        occurred_at=_ts(0),
        run_id=run_id,
        batch_id=run_id,
        record_count=0,
        event_id=explicit_id,
    )
    assert event.event_id == explicit_id
