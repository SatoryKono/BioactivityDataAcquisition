"""P02 F3/F4: expected preparation errors must leave aggregate state intact."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import patch
from uuid import UUID

import pytest

from bioetl.domain.aggregates import Batch, PipelineRun
from bioetl.domain.aggregates.batch import BatchStatus
from bioetl.domain.aggregates.pipeline_run import PipelineRunState
from bioetl.domain.medallion import Layer
from bioetl.domain.types import RunID, RunType

pytestmark = pytest.mark.unit
NOW = datetime(2026, 10, 7, tzinfo=UTC)
RUN = RunID(UUID(int=1))


def successful_run() -> PipelineRun:
    run = PipelineRun(RUN, RunType.INCREMENTAL)
    run.start(NOW)
    run.record_stage_success(
        "extract", started_at=NOW, completed_at=NOW + timedelta(seconds=1)
    )
    return run


def run_state(run: PipelineRun) -> tuple[object, ...]:
    return run.status, run.started_at, run.ended_at, run.stages, tuple(run._events)


@pytest.mark.parametrize(
    "end", [NOW.replace(tzinfo=None), NOW - timedelta(seconds=1), NOW]
)
def test_invalid_completion_preserves_entire_run(end: datetime) -> None:
    run = successful_run()
    before = run_state(run)
    with pytest.raises(ValueError):
        run.complete(end)
    assert run_state(run) == before


@pytest.mark.parametrize(
    "operation,event_name",
    [
        ("complete", "PipelineCompleted"),
        ("fail", "PipelineFailed"),
        ("shutdown", "PipelineShutdown"),
    ],
)
def test_run_event_preparation_error_is_atomic(operation: str, event_name: str) -> None:
    run = successful_run()
    before = run_state(run)
    with patch(
        f"bioetl.domain.aggregates.pipeline_run.{event_name}",
        side_effect=ValueError("prepare"),
    ):
        with pytest.raises(ValueError, match="prepare"):
            if operation == "complete":
                run.complete(NOW + timedelta(seconds=2))
            elif operation == "fail":
                run.fail("failure", failed_at=NOW + timedelta(seconds=2))
            else:
                run.shutdown(NOW + timedelta(seconds=2))
    assert run_state(run) == before


def test_failed_stage_preparation_does_not_replace_running_stage() -> None:
    run = PipelineRun(RUN, RunType.INCREMENTAL)
    run.start(NOW)
    run.record_stage_start("extract", NOW)
    before = run_state(run)
    with patch(
        "bioetl.domain.aggregates.pipeline_run_stage_result.PipelineFailed",
        side_effect=ValueError("prepare"),
    ):
        with pytest.raises(ValueError, match="prepare"):
            run.record_stage_failure("extract", "bad", started_at=NOW, completed_at=NOW)
    assert run_state(run) == before


def test_completion_orders_utc_instants_and_allows_overlapping_stages() -> None:
    run = successful_run()
    offset = timezone(timedelta(hours=2))
    run.record_stage_success(
        "overlap",
        started_at=NOW.astimezone(offset),
        completed_at=(NOW + timedelta(seconds=2)).astimezone(offset),
    )
    run.complete((NOW + timedelta(seconds=3)).astimezone(offset))
    assert run.status == PipelineRunState.COMPLETED
    assert run.duration_seconds == 3
    assert run.collect_events()[0].duration_seconds == 3


@pytest.mark.parametrize("operation", ["fail", "shutdown"])
def test_failure_and_shutdown_do_not_require_successful_stages(operation: str) -> None:
    run = PipelineRun(RUN, RunType.INCREMENTAL)
    run.start(NOW)
    run.record_stage_start("unfinished", NOW)
    if operation == "fail":
        run.fail("bad", failed_at=NOW)
    else:
        run.shutdown(NOW)
    assert run.status in {PipelineRunState.FAILED, PipelineRunState.SHUTDOWN}
    assert len(run.collect_events()) == 1


@pytest.mark.parametrize("event_name", ["BatchSealed", "BatchWritten", "BatchFailed"])
def test_batch_event_preparation_error_preserves_state(event_name: str) -> None:
    batch = Batch.create(RUN, created_at=NOW)
    batch.collect_events()
    if event_name != "BatchSealed":
        batch.seal_with_counts(
            record_count=3, valid_count=2, quarantined_count=1, sealed_at=NOW
        )
        batch.mark_writing()
    before = (
        batch.status,
        batch._sealed_at,
        batch._sealed_valid_count,
        tuple(batch._events),
    )
    with patch(
        f"bioetl.domain.aggregates._batch_aggregate.{event_name}",
        side_effect=ValueError("prepare"),
    ):
        with pytest.raises(ValueError, match="prepare"):
            if event_name == "BatchSealed":
                batch.seal_with_counts(
                    record_count=3, valid_count=2, quarantined_count=1, sealed_at=NOW
                )
            elif event_name == "BatchWritten":
                batch.mark_committed(Layer.SILVER, NOW)
            else:
                batch.mark_failed(Layer.SILVER, "bad", failed_at=NOW)
    assert (
        batch.status,
        batch._sealed_at,
        batch._sealed_valid_count,
        tuple(batch._events),
    ) == before


@pytest.mark.parametrize("fail", [False, True])
def test_batch_append_observes_target_state_and_runtime_counts(fail: bool) -> None:
    batch = Batch.create(RUN, created_at=NOW)
    observed: list[tuple[object, ...]] = []

    class ObservedQueue(list):
        def append(self, event: object) -> None:
            observed.append((batch.status, batch._sealed_at, batch._sealed_valid_count))
            super().append(event)

    batch._events = ObservedQueue()
    batch.seal_with_counts(
        record_count=3, valid_count=2, quarantined_count=1, sealed_at=NOW
    )
    assert observed[0] == (BatchStatus.SEALED, NOW, 2)
    batch.mark_writing()
    if fail:
        batch.mark_failed(Layer.SILVER, "bad", failed_at=NOW)
        assert observed[1][0] == BatchStatus.FAILED
    else:
        batch.mark_committed(Layer.SILVER, NOW)
        assert observed[1][0] == BatchStatus.COMMITTED
        assert batch.collect_events()[-1].record_count == 2
