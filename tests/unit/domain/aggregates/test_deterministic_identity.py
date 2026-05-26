"""Regression tests for replay-safe aggregate and domain event identities."""

from __future__ import annotations

from datetime import UTC, datetime

from bioetl.domain.aggregates.batch import Batch
from bioetl.domain.aggregates.events import BatchCreated
from bioetl.domain.aggregates.quarantine_entry import QuarantineEntry
from bioetl.domain.types import BatchID, RunID
from tests.helpers.deterministic_ids import deterministic_uuid_value

_EXPECTED_GOLDEN = {
    "batch_create_batch_id": "3f700e91-4464-5a8d-95c0-379bce6e1a5d",
    "batch_created_event_id": "bee1d5c9-eed4-5029-b1b9-0a1d06bba186",
    "quarantine_entry_id": "930956c0-4a9c-53ad-8fdf-9a150c1ab9d1",
    "quarantine_payload_hash": (
        "73b5df1d5d2cd480a7fcb5935b2a9429f1889a10d877d1b05d29158369cf4cce"
    ),
}


def _ts() -> datetime:
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _run_id() -> RunID:
    return RunID(deterministic_uuid_value("unit.domain.deterministic_identity.run"))


def _batch_id() -> BatchID:
    return BatchID(deterministic_uuid_value("unit.domain.deterministic_identity.batch"))


def test_batch_create_derives_same_batch_id_from_same_explicit_inputs() -> None:
    """Replay of the same batch creation inputs should preserve batch identity."""
    first = Batch.create(run_id=_run_id(), start_index=10, created_at=_ts())
    second = Batch.create(run_id=_run_id(), start_index=10, created_at=_ts())

    assert first.batch_id == second.batch_id


def test_domain_event_default_id_is_content_derived() -> None:
    """Events emitted from identical inputs should have identical event IDs."""
    first = BatchCreated(
        occurred_at=_ts(),
        run_id=_run_id(),
        batch_id=_batch_id(),
        record_count=3,
    )
    second = BatchCreated(
        occurred_at=_ts(),
        run_id=_run_id(),
        batch_id=_batch_id(),
        record_count=3,
    )

    assert first.event_id == second.event_id
    assert first.event_id


def test_quarantine_entry_create_derives_same_entry_id_from_same_inputs() -> None:
    """Replay of the same quarantine creation inputs should preserve entry identity."""
    first = QuarantineEntry.create(
        pipeline_name="test_pipeline",
        error_code="SCHEMA_VIOLATION",
        payload={"id": "bad-record", "nested": {"b": 2, "a": 1}},
        run_id=_run_id(),
        batch_id=_batch_id(),
        created_at=_ts(),
        metadata={"source": "unit"},
    )
    second = QuarantineEntry.create(
        pipeline_name="test_pipeline",
        error_code="SCHEMA_VIOLATION",
        payload={"nested": {"a": 1, "b": 2}, "id": "bad-record"},
        run_id=_run_id(),
        batch_id=_batch_id(),
        created_at=_ts(),
        metadata={"source": "unit"},
    )

    assert first.entry_id == second.entry_id
    assert first.payload_hash == second.payload_hash
    assert len(first.entry_id) == 36


def test_deterministic_identity_golden_contract_is_stable() -> None:
    """Pinned values catch accidental namespace or canonicalization drift."""
    batch = Batch.create(run_id=_run_id(), start_index=10, created_at=_ts())
    event = BatchCreated(
        occurred_at=_ts(),
        run_id=_run_id(),
        batch_id=_batch_id(),
        record_count=3,
    )
    quarantine = QuarantineEntry.create(
        pipeline_name="test_pipeline",
        error_code="SCHEMA_VIOLATION",
        payload={"id": "bad-record", "nested": {"b": 2, "a": 1}},
        run_id=_run_id(),
        batch_id=_batch_id(),
        created_at=_ts(),
        metadata={"source": "unit"},
    )

    assert str(batch.batch_id) == _EXPECTED_GOLDEN["batch_create_batch_id"]
    assert str(event.event_id) == _EXPECTED_GOLDEN["batch_created_event_id"]
    assert quarantine.entry_id == _EXPECTED_GOLDEN["quarantine_entry_id"]
    assert quarantine.payload_hash == _EXPECTED_GOLDEN["quarantine_payload_hash"]
