import pytest
from datetime import datetime, UTC

from bioetl.domain.aggregates.events import (
    PipelineCompleted,
    PipelineFailed,
    PipelineShutdown,
    BatchCreated,
    BatchSealed,
    BatchWritten,
    BatchFailed,
    RecordQuarantined,
    QuarantineEntryCreated,
    QuarantineEntryResolved,
)
from bioetl.domain.types import RunID, BatchID, ContentHash
from bioetl.domain.medallion import Layer


pytestmark = pytest.mark.unit


def _ts():
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _run_id():
    return RunID("00000000-0000-0000-0000-000000000000")


def _batch_id():
    return BatchID("00000000-0000-0000-0000-000000000001")


# PipelineCompleted
def test_pipeline_completed_valid():
    pc = PipelineCompleted(
        occurred_at=_ts(),
        run_id=_run_id(),
        pipeline_name="test",
        records_processed=0,
        duration_seconds=0.0,
        stages_count=0,
    )
    assert pc.records_processed == 0


@pytest.mark.parametrize(
    "records_processed, duration_seconds, stages_count, expected_error",
    [
        (-1, 0.0, 0, "records_processed cannot be negative"),
        (0, -1.0, 0, "duration_seconds cannot be negative"),
        (0, 0.0, -1, "stages_count cannot be negative"),
    ],
)
def test_pipeline_completed_invalid(
    records_processed, duration_seconds, stages_count, expected_error
):
    with pytest.raises(ValueError, match=expected_error):
        PipelineCompleted(
            occurred_at=_ts(),
            run_id=_run_id(),
            pipeline_name="test",
            records_processed=records_processed,
            duration_seconds=duration_seconds,
            stages_count=stages_count,
        )


# PipelineFailed
def test_pipeline_failed_valid():
    pf = PipelineFailed(
        occurred_at=_ts(),
        run_id=_run_id(),
        pipeline_name="test",
        failed_stage="extract",
        error="failed",
    )
    assert pf.failed_stage == "extract"


@pytest.mark.parametrize(
    "failed_stage, error, expected_error",
    [
        ("", "error", "failed_stage cannot be empty"),
        ("extract", "", "error cannot be empty"),
    ],
)
def test_pipeline_failed_invalid(failed_stage, error, expected_error):
    with pytest.raises(ValueError, match=expected_error):
        PipelineFailed(
            occurred_at=_ts(),
            run_id=_run_id(),
            pipeline_name="test",
            failed_stage=failed_stage,
            error=error,
        )


# PipelineShutdown
def test_pipeline_shutdown_valid():
    ps = PipelineShutdown(
        occurred_at=_ts(), run_id=_run_id(), pipeline_name="test", records_processed=0
    )
    assert ps.records_processed == 0


def test_pipeline_shutdown_invalid():
    with pytest.raises(ValueError, match="records_processed cannot be negative"):
        PipelineShutdown(
            occurred_at=_ts(),
            run_id=_run_id(),
            pipeline_name="test",
            records_processed=-1,
        )


# BatchCreated
def test_batch_created_valid():
    bc = BatchCreated(
        occurred_at=_ts(), run_id=_run_id(), batch_id=_batch_id(), record_count=0
    )
    assert bc.record_count == 0


def test_batch_created_invalid():
    with pytest.raises(ValueError, match="record_count cannot be negative"):
        BatchCreated(
            occurred_at=_ts(), run_id=_run_id(), batch_id=_batch_id(), record_count=-1
        )


# BatchSealed
def test_batch_sealed_valid():
    bs = BatchSealed(
        occurred_at=_ts(),
        run_id=_run_id(),
        batch_id=_batch_id(),
        record_count=10,
        valid_count=8,
        quarantined_count=2,
    )
    assert bs.record_count == 10


@pytest.mark.parametrize(
    "record_count, valid_count, quarantined_count, expected_error",
    [
        (-1, 0, 0, "counts must be non-negative"),
        (0, -1, 0, "counts must be non-negative"),
        (0, 0, -1, "counts must be non-negative"),
        (10, 8, 1, r"valid_count \+ quarantined_count must equal record_count"),
    ],
)
def test_batch_sealed_invalid(
    record_count, valid_count, quarantined_count, expected_error
):
    with pytest.raises(ValueError, match=expected_error):
        BatchSealed(
            occurred_at=_ts(),
            run_id=_run_id(),
            batch_id=_batch_id(),
            record_count=record_count,
            valid_count=valid_count,
            quarantined_count=quarantined_count,
        )


# BatchWritten
def test_batch_written_valid():
    bw = BatchWritten(
        occurred_at=_ts(),
        run_id=_run_id(),
        batch_id=_batch_id(),
        layer=Layer.BRONZE,
        record_count=0,
    )
    assert bw.record_count == 0


def test_batch_written_invalid():
    with pytest.raises(ValueError, match="record_count cannot be negative"):
        BatchWritten(
            occurred_at=_ts(),
            run_id=_run_id(),
            batch_id=_batch_id(),
            layer=Layer.BRONZE,
            record_count=-1,
        )


# BatchFailed
def test_batch_failed_valid():
    bf = BatchFailed(
        occurred_at=_ts(),
        run_id=_run_id(),
        batch_id=_batch_id(),
        layer=Layer.BRONZE,
        error="failed",
    )
    assert bf.error == "failed"


def test_batch_failed_invalid():
    with pytest.raises(ValueError, match="error cannot be empty"):
        BatchFailed(
            occurred_at=_ts(),
            run_id=_run_id(),
            batch_id=_batch_id(),
            layer=Layer.BRONZE,
            error="",
        )


# RecordQuarantined
def test_record_quarantined_valid():
    rq = RecordQuarantined(
        occurred_at=_ts(),
        run_id=_run_id(),
        batch_id=_batch_id(),
        record_id="r1",
        error_code="E01",
        error_message="failed",
    )
    assert rq.error_message == "failed"


def test_record_quarantined_invalid():
    with pytest.raises(ValueError, match="error_message cannot be empty"):
        RecordQuarantined(
            occurred_at=_ts(),
            run_id=_run_id(),
            batch_id=_batch_id(),
            record_id="r1",
            error_code="E01",
            error_message="",
        )


# QuarantineEntryCreated
def test_quarantine_entry_created_valid():
    qc = QuarantineEntryCreated(
        occurred_at=_ts(),
        run_id=_run_id(),
        batch_id=_batch_id(),
        pipeline_name="test",
        error_code="E01",
        payload_hash=ContentHash("abc"),
    )
    assert qc.error_code == "E01"


def test_quarantine_entry_created_invalid():
    with pytest.raises(ValueError, match="error_code cannot be empty"):
        QuarantineEntryCreated(
            occurred_at=_ts(),
            run_id=_run_id(),
            batch_id=_batch_id(),
            pipeline_name="test",
            error_code="",
            payload_hash=ContentHash("abc"),
        )


# QuarantineEntryResolved
def test_quarantine_entry_resolved_valid():
    qr = QuarantineEntryResolved(
        occurred_at=_ts(), run_id=_run_id(), entry_id="e1", resolution="reprocessed"
    )
    assert qr.resolution == "reprocessed"
    qr2 = QuarantineEntryResolved(
        occurred_at=_ts(), run_id=_run_id(), entry_id="e1", resolution="ignored"
    )
    assert qr2.resolution == "ignored"


def test_quarantine_entry_resolved_invalid():
    with pytest.raises(ValueError, match="invalid resolution: unknown"):
        QuarantineEntryResolved(
            occurred_at=_ts(), run_id=_run_id(), entry_id="e1", resolution="unknown"
        )


@pytest.mark.parametrize("duration", [float("nan"), float("inf"), float("-inf")])
def test_pipeline_completed_rejects_nonfinite_duration_with_explicit_id(duration):
    with pytest.raises(ValueError, match="duration_seconds"):
        PipelineCompleted(
            occurred_at=_ts(),
            event_id="explicit",
            run_id=_run_id(),
            pipeline_name="pipeline",
            records_processed=0,
            duration_seconds=duration,
            stages_count=0,
        )
