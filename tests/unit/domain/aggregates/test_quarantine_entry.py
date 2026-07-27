"""Tests for QuarantineEntry aggregate invariants.

Tests verify that:
1. payload_hash is unique within a pipeline (enforced by storage)
2. Status transitions: NEW -> IGNORED or NEW -> REPROCESSED
3. Resolution metadata is required when marking as resolved
4. payload cannot be modified after creation
5. error_code is required and immutable

Constructor surface width is governed by ADR-051 (intentional_exception).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bioetl.domain.aggregates.quarantine_entry import (
    QuarantineEntry,
    QuarantineStatus,
    ResolutionInfo,
)
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import BatchID, ContentHash, RunID
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = pytest.mark.unit


def _ts(offset_seconds: int = 0) -> datetime:
    """Return deterministic UTC timestamps for quarantine tests."""
    return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=offset_seconds)


@pytest.fixture
def run_id() -> RunID:
    """Create a test run ID."""
    return RunID(deterministic_uuid_value("unit.quarantine_entry.run_id"))


@pytest.fixture
def batch_id() -> BatchID:
    """Create a test batch ID."""
    return BatchID(deterministic_uuid_value("unit.quarantine_entry.batch_id"))


@pytest.fixture
def quarantine_entry(run_id: RunID, batch_id: BatchID) -> QuarantineEntry:
    """Create a test quarantine entry."""
    return QuarantineEntry.create(
        pipeline_name="test_pipeline",
        error_code="SCHEMA_VIOLATION",
        payload={"id": "bad-record", "value": "invalid"},
        run_id=run_id,
        batch_id=batch_id,
        created_at=_ts(0),
    )


# ──────────────────────────────────────────────────────────────────────────────
# ResolutionInfo Value Object Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestResolutionInfoInvariants:
    """Tests for ResolutionInfo value object invariants."""

    def test_invalid_resolution_type_rejected(self) -> None:
        """Invariant: resolution_type must be 'ignored' or 'reprocessed'."""
        with pytest.raises(ValueError, match="Invalid resolution_type"):
            ResolutionInfo(
                resolution_type="deleted",  # Invalid
                resolved_at=_ts(1),
            )

    def test_valid_ignored_resolution(self) -> None:
        """Valid ignored resolution should be created."""
        info = ResolutionInfo(
            resolution_type="ignored",
            resolved_at=_ts(1),
            reason="Known bad data",
        )
        assert info.resolution_type == "ignored"

    def test_valid_reprocessed_resolution(self) -> None:
        """Valid reprocessed resolution should be created."""
        info = ResolutionInfo(
            resolution_type="reprocessed",
            resolved_at=_ts(1),
            new_record_id="silver:123",
        )
        assert info.resolution_type == "reprocessed"
        assert info.new_record_id == "silver:123"

    def test_quarantine_entry_resolution_info_is_immutable(self) -> None:
        """ResolutionInfo should be frozen (immutable)."""
        info = ResolutionInfo(
            resolution_type="ignored",
            resolved_at=_ts(1),
        )
        with pytest.raises(AttributeError):
            info.resolution_type = "reprocessed"  # type: ignore


# ──────────────────────────────────────────────────────────────────────────────
# Constructor Validation Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineEntryConstructorValidation:
    """Tests for constructor validation."""

    def test_entry_id_required(self, run_id: RunID, batch_id: BatchID) -> None:
        """Invariant: entry_id is required."""
        with pytest.raises(ValueError, match="entry_id is required"):
            QuarantineEntry(
                entry_id="",  # Empty
                pipeline_name="test",
                error_code="ERR",
                payload={"id": "1"},
                payload_hash=ContentHash("abc123"),
                run_id=run_id,
                batch_id=batch_id,
                created_at=_ts(0),
            )

    def test_pipeline_name_required(self, run_id: RunID, batch_id: BatchID) -> None:
        """Invariant: pipeline_name is required."""
        with pytest.raises(ValueError, match="pipeline_name is required"):
            QuarantineEntry(
                entry_id="entry-1",
                pipeline_name="",  # Empty
                error_code="ERR",
                payload={"id": "1"},
                payload_hash=ContentHash("abc123"),
                run_id=run_id,
                batch_id=batch_id,
                created_at=_ts(0),
            )

    def test_error_code_required(self, run_id: RunID, batch_id: BatchID) -> None:
        """Invariant: error_code is required."""
        with pytest.raises(ValueError, match="error_code is required"):
            QuarantineEntry(
                entry_id="entry-1",
                pipeline_name="test",
                error_code="",  # Empty
                payload={"id": "1"},
                payload_hash=ContentHash("abc123"),
                run_id=run_id,
                batch_id=batch_id,
                created_at=_ts(0),
            )

    def test_payload_cannot_be_empty(self, run_id: RunID, batch_id: BatchID) -> None:
        """Invariant: payload cannot be empty."""
        with pytest.raises(ValueError, match="payload cannot be empty"):
            QuarantineEntry(
                entry_id="entry-1",
                pipeline_name="test",
                error_code="ERR",
                payload={},  # Empty
                payload_hash=ContentHash("abc123"),
                run_id=run_id,
                batch_id=batch_id,
                created_at=_ts(0),
            )


# ──────────────────────────────────────────────────────────────────────────────
# State Transition Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineEntryStateTransitions:
    """Tests for QuarantineEntry state machine transitions."""

    def test_initial_status_is_new(self, quarantine_entry: QuarantineEntry) -> None:
        """New entry should be in NEW status."""
        assert quarantine_entry.status == QuarantineStatus.NEW
        assert quarantine_entry.resolution_info is None

    def test_start_review_transitions_to_under_review(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """start_review() should transition NEW -> UNDER_REVIEW."""
        quarantine_entry.start_review()
        assert quarantine_entry.status == QuarantineStatus.UNDER_REVIEW

    def test_cannot_start_review_twice(self, quarantine_entry: QuarantineEntry) -> None:
        """Invariant: Cannot start review on non-NEW entry."""
        quarantine_entry.start_review()

        with pytest.raises(InvalidStateError, match="Cannot start review"):
            quarantine_entry.start_review()

    def test_mark_ignored_from_new(self, quarantine_entry: QuarantineEntry) -> None:
        """Should transition NEW -> IGNORED."""
        quarantine_entry.mark_ignored(reason="Known bad data", resolved_at=_ts(10))

        assert quarantine_entry.status == QuarantineStatus.IGNORED
        assert quarantine_entry.resolution_info is not None
        assert quarantine_entry.resolution_info.reason == "Known bad data"
        assert quarantine_entry.resolution_info.resolved_at == _ts(10)

    def test_mark_ignored_from_under_review(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """Should transition UNDER_REVIEW -> IGNORED."""
        quarantine_entry.start_review()
        quarantine_entry.mark_ignored(resolved_at=_ts(10))

        assert quarantine_entry.status == QuarantineStatus.IGNORED

    def test_mark_reprocessed_from_new(self, quarantine_entry: QuarantineEntry) -> None:
        """Should transition NEW -> REPROCESSED."""
        quarantine_entry.mark_reprocessed(
            new_record_id="silver:456",
            resolved_at=_ts(10),
        )

        assert quarantine_entry.status == QuarantineStatus.REPROCESSED
        assert quarantine_entry.resolution_info is not None
        assert quarantine_entry.resolution_info.new_record_id == "silver:456"
        assert quarantine_entry.resolution_info.resolved_at == _ts(10)

    def test_quarantine_entry_mark_reprocessed_requires_new_record_id(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """Invariant: new_record_id is required for reprocessing."""
        with pytest.raises(ValueError, match="new_record_id is required"):
            quarantine_entry.mark_reprocessed(new_record_id="", resolved_at=_ts(10))


# ──────────────────────────────────────────────────────────────────────────────
# Terminal State Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineEntryTerminalStates:
    """Tests for terminal state behavior."""

    def test_cannot_resolve_already_ignored(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """Invariant: Cannot resolve an already ignored entry."""
        quarantine_entry.mark_ignored(resolved_at=_ts(10))

        with pytest.raises(InvalidStateError, match="entry is in status ignored"):
            quarantine_entry.mark_reprocessed(
                new_record_id="test",
                resolved_at=_ts(11),
            )

    def test_cannot_resolve_already_reprocessed(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """Invariant: Cannot resolve an already reprocessed entry."""
        quarantine_entry.mark_reprocessed(new_record_id="test", resolved_at=_ts(10))

        with pytest.raises(InvalidStateError, match="entry is in status reprocessed"):
            quarantine_entry.mark_ignored(resolved_at=_ts(11))

    def test_cannot_modify_metadata_after_resolution(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """Invariant: Cannot modify metadata after resolution."""
        quarantine_entry.mark_ignored(resolved_at=_ts(10))

        with pytest.raises(InvalidStateError, match="terminal status"):
            quarantine_entry.add_metadata("key", "value")

    def test_can_add_metadata_before_resolution(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """Should allow adding metadata before resolution."""
        quarantine_entry.add_metadata("analysis", "needs review")

        assert "analysis" in quarantine_entry.metadata


# ──────────────────────────────────────────────────────────────────────────────
# Expiration Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineEntryExpiration:
    """Tests for expiration behavior."""

    def test_mark_expired_from_new(self, quarantine_entry: QuarantineEntry) -> None:
        """Should transition NEW -> EXPIRED."""
        quarantine_entry.mark_expired(expired_at=_ts(10))

        assert quarantine_entry.status == QuarantineStatus.EXPIRED
        assert quarantine_entry.resolution_info is not None
        assert quarantine_entry.resolution_info.resolved_at == _ts(10)

    def test_age_requires_explicit_reference_until_resolved(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """Unresolved entry age should require an explicit reference timestamp."""
        assert quarantine_entry.age_seconds is None
        assert quarantine_entry.age_seconds_at(_ts(10)) == pytest.approx(10.0)

    def test_resolved_entry_has_stable_age(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """Resolved entry should expose deterministic age from stored state."""
        quarantine_entry.mark_ignored(resolved_at=_ts(10))

        assert quarantine_entry.age_seconds == pytest.approx(10.0)
        assert quarantine_entry.age_seconds_at(_ts(20)) == pytest.approx(20.0)

    def test_cannot_expire_already_resolved(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """Invariant: Cannot expire an already resolved entry."""
        quarantine_entry.mark_ignored(resolved_at=_ts(10))

        with pytest.raises(InvalidStateError, match="already in terminal status"):
            quarantine_entry.mark_expired(expired_at=_ts(11))


# ──────────────────────────────────────────────────────────────────────────────
# Encapsulation Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineEntryEncapsulation:
    """Tests for field encapsulation."""

    def test_entry_id_is_immutable(self, quarantine_entry: QuarantineEntry) -> None:
        """Invariant: entry_id cannot be changed."""
        with pytest.raises(AttributeError):
            quarantine_entry.entry_id = "new-id"  # type: ignore

    def test_error_code_is_immutable(self, quarantine_entry: QuarantineEntry) -> None:
        """Invariant: error_code cannot be changed."""
        with pytest.raises(AttributeError):
            quarantine_entry.error_code = "NEW_ERROR"  # type: ignore

    def test_payload_returns_copy(self, quarantine_entry: QuarantineEntry) -> None:
        """Invariant: payload returns a copy, not the original."""
        payload = quarantine_entry.payload
        payload["new_key"] = "new_value"

        assert "new_key" not in quarantine_entry.payload

    def test_nested_payload_is_detached_from_constructor_and_accessor(
        self,
        run_id: RunID,
        batch_id: BatchID,
    ) -> None:
        """Invariant: nested quarantine payload objects cannot mutate after capture."""
        source_payload = {
            "id": "bad-record",
            "nested": {"values": ["original"]},
        }
        entry = QuarantineEntry.create(
            pipeline_name="test_pipeline",
            error_code="SCHEMA_VIOLATION",
            payload=source_payload,
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )
        expected_hash = entry.payload_hash

        source_payload["nested"]["values"].append("mutated")  # type: ignore[index, union-attr]
        payload_view = entry.payload
        payload_view["nested"]["values"].append("accessor-mutation")  # type: ignore[index, union-attr]

        assert entry.payload == {"id": "bad-record", "nested": {"values": ["original"]}}
        assert entry.payload_hash == expected_hash

    def test_nested_metadata_is_detached_from_constructor_and_accessor(
        self,
        run_id: RunID,
        batch_id: BatchID,
    ) -> None:
        """Invariant: metadata access is defensive for nested replay diagnostics."""
        metadata = {"diagnostics": {"fields": ["target_id"]}}
        entry = QuarantineEntry.create(
            pipeline_name="test_pipeline",
            error_code="SCHEMA_VIOLATION",
            payload={"id": "bad-record"},
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
            metadata=metadata,
        )

        metadata["diagnostics"]["fields"].append("mutated")  # type: ignore[index, union-attr]
        metadata_view = entry.metadata
        metadata_view["diagnostics"]["fields"].append("view-mutation")  # type: ignore[index, union-attr]

        assert entry.metadata == {"diagnostics": {"fields": ["target_id"]}}

    def test_payload_hash_is_immutable(self, quarantine_entry: QuarantineEntry) -> None:
        """Invariant: payload_hash cannot be changed."""
        with pytest.raises(AttributeError):
            quarantine_entry.payload_hash = ContentHash("newhash")  # type: ignore

    def test_entry_encapsulation__returns_copy__3f32547b(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """Invariant: metadata returns a copy."""
        metadata = quarantine_entry.metadata
        metadata["new_key"] = "new_value"

        assert "new_key" not in quarantine_entry.metadata


# ──────────────────────────────────────────────────────────────────────────────
# Domain Events Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineEntryDomainEvents:
    """Tests for domain event generation."""

    def test_create_emits_quarantine_entry_created_event(
        self, run_id: RunID, batch_id: BatchID
    ) -> None:
        """create() should emit QuarantineEntryCreated event."""
        entry = QuarantineEntry.create(
            pipeline_name="test",
            error_code="ERR",
            payload={"id": "1"},
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )

        events = entry.collect_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "QuarantineEntryCreated"
        assert events[0].occurred_at == _ts(0)

    def test_resolve_emits_quarantine_entry_resolved_event(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """Resolution should emit QuarantineEntryResolved event."""
        quarantine_entry.collect_events()  # Clear creation event
        quarantine_entry.mark_ignored(reason="Test", resolved_at=_ts(10))

        events = quarantine_entry.collect_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "QuarantineEntryResolved"
        assert events[0].resolution == "ignored"
        assert events[0].occurred_at == _ts(10)

    def test_quarantine_entry_collect_events_clears_event_list(
        self, quarantine_entry: QuarantineEntry
    ) -> None:
        """collect_events() should clear internal list."""
        first_collection = quarantine_entry.collect_events()
        second_collection = quarantine_entry.collect_events()

        assert len(first_collection) == 1
        assert len(second_collection) == 0


# ──────────────────────────────────────────────────────────────────────────────
# QuarantineStatus Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineStatus:
    """Tests for QuarantineStatus enum behavior."""

    def test_quarantine_status__terminal_statuses__2200c9ea(self) -> None:
        """Terminal statuses should return True for is_terminal()."""
        assert QuarantineStatus.IGNORED.is_terminal()
        assert QuarantineStatus.REPROCESSED.is_terminal()
        assert QuarantineStatus.EXPIRED.is_terminal()

    def test_quarantine_status__terminal_statuses__48a78d4b(self) -> None:
        """Non-terminal statuses should return False for is_terminal()."""
        assert not QuarantineStatus.NEW.is_terminal()
        assert not QuarantineStatus.UNDER_REVIEW.is_terminal()

    def test_resolvable_statuses(self) -> None:
        """Resolvable statuses should return True for can_resolve()."""
        assert QuarantineStatus.NEW.can_resolve()
        assert QuarantineStatus.UNDER_REVIEW.can_resolve()
        assert not QuarantineStatus.IGNORED.can_resolve()
        assert not QuarantineStatus.REPROCESSED.can_resolve()


# ──────────────────────────────────────────────────────────────────────────────
# Factory Method Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineEntryFactory:
    """Tests for factory method behavior."""

    def test_create_generates_entry_id(self, run_id: RunID, batch_id: BatchID) -> None:
        """create() should generate unique entry_id."""
        entry = QuarantineEntry.create(
            pipeline_name="test",
            error_code="ERR",
            payload={"id": "1"},
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )

        assert entry.entry_id  # Not empty
        assert len(entry.entry_id) == 36  # UUID format

    def test_create_computes_payload_hash(
        self, run_id: RunID, batch_id: BatchID
    ) -> None:
        """create() should compute payload_hash from payload."""
        entry = QuarantineEntry.create(
            pipeline_name="test",
            error_code="ERR",
            payload={"id": "1"},
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )

        assert entry.payload_hash
        assert len(entry.payload_hash) == 64  # SHA256 hex

    def test_same_payload_produces_same_hash(
        self, run_id: RunID, batch_id: BatchID
    ) -> None:
        """Same payload should produce same hash."""
        entry1 = QuarantineEntry.create(
            pipeline_name="test",
            error_code="ERR",
            payload={"id": "1", "value": 100},
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )
        entry2 = QuarantineEntry.create(
            pipeline_name="test",
            error_code="ERR",
            payload={"id": "1", "value": 100},
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(1),
        )

        assert entry1.payload_hash == entry2.payload_hash

    def test_nested_payload_hash_is_replay_stable_across_mapping_order(
        self,
        run_id: RunID,
        batch_id: BatchID,
    ) -> None:
        """Replay envelope: canonical payload hashing ignores mapping insertion order."""
        first = QuarantineEntry.create(
            pipeline_name="test",
            error_code="ERR",
            payload={"id": "1", "nested": {"b": [2, 1], "a": 1}},
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )
        second = QuarantineEntry.create(
            pipeline_name="test",
            error_code="ERR",
            payload={"nested": {"a": 1, "b": [2, 1]}, "id": "1"},
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(1),
        )

        assert first.payload_hash == second.payload_hash
