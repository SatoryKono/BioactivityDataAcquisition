"""P02 F1/F7: immutable events and detached quarantine metadata."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

import pytest
from structlog.processors import JSONRenderer

from bioetl.domain.aggregates import QuarantineEntry
from bioetl.domain.aggregates.events import QuarantineEntryCreated
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.observability_event_mapping import (
    map_domain_event_to_observability_event,
)
from bioetl.domain.types import BatchID, ContentHash, RunID

pytestmark = pytest.mark.unit
NOW = datetime(2026, 10, 7, tzinfo=UTC)
RUN = RunID(UUID(int=1))
BATCH = BatchID(UUID(int=2))


def make_entry(metadata: dict[str, object] | None = None) -> QuarantineEntry:
    return QuarantineEntry.create(
        "p",
        "E",
        {"value": 1e-7},
        RUN,
        BATCH,
        created_at=NOW,
        metadata=metadata,
    )


@pytest.mark.parametrize("explicit_id", ["", "persisted-event-id"])
def test_direct_event_detaches_metadata_before_identity(explicit_id: str) -> None:
    metadata = {"nested": {"items": [1, 1e-7]}}
    event = QuarantineEntryCreated(
        occurred_at=NOW,
        run_id=RUN,
        batch_id=BATCH,
        pipeline_name="p",
        error_code="E",
        payload_hash=ContentHash("a" * 64),
        metadata=metadata,
        event_id=explicit_id,
    )
    identity = event.event_id
    metadata["nested"]["items"].append(2)
    assert event.metadata == {"nested": {"items": [1, 1e-7]}}
    assert event.event_id == identity
    if explicit_id:
        assert identity == explicit_id
    with pytest.raises(TypeError):
        event.metadata["nested"]["items"][0] = 99  # type: ignore[index]


def test_factory_event_and_real_json_projection_are_independent() -> None:
    metadata = {"nested": [1]}
    entry = make_entry(metadata)
    event = entry.collect_events()[0]
    identity = event.event_id
    metadata["nested"].append(2)
    entry.start_review()
    entry.add_metadata("nested", [9])
    envelope = map_domain_event_to_observability_event(event)
    rendered = JSONRenderer()(None, "warning", dict(envelope.context))
    stored = json.loads(rendered)
    assert stored["metadata"] == {"nested": [1]}
    assert event.event_id == identity
    envelope.context["metadata"]["nested"].append(3)
    assert event.metadata == {"nested": [1]}


def test_metadata_projection_normalizes_nested_identity_scalars() -> None:
    class IdentityValue(Enum):
        TIMESTAMP = NOW
        IDENTIFIER = UUID("ABCDEF01-2345-6789-ABCD-EF0123456789")

    metadata = {
        "timestamp": NOW,
        "identifier": IdentityValue.IDENTIFIER.value,
        "nested": [{"values": (IdentityValue.TIMESTAMP, IdentityValue.IDENTIFIER)}],
        "primitives": [None, True, 3, 1.5, "text"],
    }
    event = QuarantineEntryCreated(
        occurred_at=NOW,
        run_id=RUN,
        batch_id=BATCH,
        pipeline_name="p",
        error_code="E",
        payload_hash=ContentHash("a" * 64),
        metadata=metadata,
        event_id="persisted-event-id",
    )
    identity = event.event_id
    envelope = map_domain_event_to_observability_event(event)
    expected = {
        "timestamp": NOW.isoformat(),
        "identifier": "abcdef01-2345-6789-abcd-ef0123456789",
        "nested": [
            {"values": [NOW.isoformat(), "abcdef01-2345-6789-abcd-ef0123456789"]}
        ],
        "primitives": [None, True, 3, 1.5, "text"],
    }
    assert envelope.context["metadata"] == expected
    assert json.loads(json.dumps(envelope.context))["metadata"] == expected
    assert (
        json.loads(JSONRenderer()(None, "warning", dict(envelope.context)))["metadata"]
        == expected
    )
    assert event.metadata == metadata
    assert event.event_id == identity


@pytest.mark.parametrize("explicit_id", ["", "persisted-event-id"])
@pytest.mark.parametrize(
    ("value", "error"),
    [
        (float("nan"), ValueError),
        (float("inf"), ValueError),
        ({1: 2}, TypeError),
        (object(), TypeError),
    ],
)
def test_event_metadata_validation_is_preserved(
    explicit_id: str, value: object, error: type[Exception]
) -> None:
    with pytest.raises(error):
        QuarantineEntryCreated(
            occurred_at=NOW,
            run_id=RUN,
            batch_id=BATCH,
            pipeline_name="p",
            error_code="E",
            payload_hash=ContentHash("a" * 64),
            metadata={"nested": [value]},
            event_id=explicit_id,
        )


@pytest.mark.parametrize("review", [False, True])
@pytest.mark.parametrize("terminal", ["ignored", "reprocessed", "expired"])
def test_added_metadata_cannot_change_after_resolution(
    review: bool,
    terminal: str,
) -> None:
    entry = make_entry()
    original_hash = entry.payload_hash
    original_payload = entry.payload
    if review:
        entry.start_review()
    metadata = {"items": [1]}
    entry.add_metadata("context", metadata)
    if terminal == "ignored":
        entry.mark_ignored(reason="reviewed", resolved_at=NOW)
    elif terminal == "reprocessed":
        entry.mark_reprocessed("replacement", resolved_at=NOW)
    else:
        entry.mark_expired(expired_at=NOW)
    metadata["items"].append(2)
    assert entry.metadata["context"] == {"items": [1]}
    copy = entry.metadata
    copy["context"]["items"].append(3)
    assert entry.metadata["context"] == {"items": [1]}
    assert entry.payload == original_payload
    assert entry.payload_hash == original_hash
    with pytest.raises(InvalidStateError):
        entry.add_metadata("new", {"items": []})


def test_metadata_updates_remain_legal_before_terminal() -> None:
    entry = make_entry()
    entry.add_metadata("value", [1])
    entry.start_review()
    entry.add_metadata("value", [2])
    assert entry.metadata["value"] == [2]


def test_copy_failure_does_not_replace_existing_metadata() -> None:
    class Uncopyable:
        def __deepcopy__(self, memo: dict[int, object]) -> object:
            raise ValueError("cannot snapshot")

    entry = make_entry()
    entry.add_metadata("context", {"original": True})
    with pytest.raises(ValueError, match="cannot snapshot"):
        entry.add_metadata("context", Uncopyable())
    assert entry.metadata["context"] == {"original": True}
