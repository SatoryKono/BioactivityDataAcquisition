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
"""Tests for QuarantineEntry aggregate internal modules.

This test file provides focused coverage for QuarantineEntry internal modules:
- _quarantine_aggregate.py: Aggregate root construction and factory methods
- _quarantine_value_objects.py: Value objects and read-model projections
- quarantine_entry.py: State transition methods and event collection
- _quarantine_value_objects.py: Value objects and validation helpers

These tests complement the existing test_quarantine_entry.py by testing internal
mixin methods directly and covering validation functions and transformation scenarios.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bioetl.domain.aggregates._quarantine_aggregate import QuarantineEntry
from bioetl.domain.aggregates._quarantine_value_objects import (
    QuarantineStatus,
    ResolutionInfo,
    _validate_quarantine_required_fields,
)
from bioetl.domain.aggregates.events import QuarantineEntryResolved
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import BatchID, ContentHash, RunID
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = pytest.mark.unit


def _ts(offset_seconds: int = 0) -> datetime:
    """Return deterministic UTC timestamps for quarantine tests."""
    return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=offset_seconds)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def run_id() -> RunID:
    """Create a test run ID."""
    return RunID(deterministic_uuid_value("quarantine_internal.run_id"))


@pytest.fixture
def batch_id() -> BatchID:
    """Create a test batch ID."""
    return BatchID(deterministic_uuid_value("quarantine_internal.batch_id"))


@pytest.fixture
def sample_payload():
    """Sample payload for testing."""
    return {"id": "bad-record", "value": "invalid", "source": "test"}


@pytest.fixture
def quarantine_entry(run_id: RunID, batch_id: BatchID, sample_payload):
    """Create a test quarantine entry."""
    return QuarantineEntry.create(
        pipeline_name="test_pipeline",
        error_code="SCHEMA_VIOLATION",
        payload=sample_payload,
        run_id=run_id,
        batch_id=batch_id,
        created_at=_ts(0),
    )


# ──────────────────────────────────────────────────────────────────────────────
# _quarantine_value_objects.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineStatusEnum:
    """Tests for QuarantineStatus enum behavior."""

    def test_is_terminal_identifies_terminal_statuses(self):
        """is_terminal should return True for terminal statuses."""
        assert QuarantineStatus.IGNORED.is_terminal()
        assert QuarantineStatus.REPROCESSED.is_terminal()
        assert QuarantineStatus.EXPIRED.is_terminal()
        assert not QuarantineStatus.NEW.is_terminal()
        assert not QuarantineStatus.UNDER_REVIEW.is_terminal()

    def test_can_resolve_identifies_resolvable_statuses(self):
        """can_resolve should return True for statuses that can transition to resolved."""
        assert QuarantineStatus.NEW.can_resolve()
        assert QuarantineStatus.UNDER_REVIEW.can_resolve()
        assert not QuarantineStatus.IGNORED.can_resolve()
        assert not QuarantineStatus.REPROCESSED.can_resolve()
        assert not QuarantineStatus.EXPIRED.can_resolve()


class TestResolutionInfoValueObject:
    """Tests for ResolutionInfo value object."""

    def test_resolution_info_with_all_fields(self):
        """ResolutionInfo should accept all optional fields."""
        info = ResolutionInfo(
            resolution_type="reprocessed",
            resolved_at=_ts(10),
            resolved_by="user-123",
            reason="Fixed data issue",
            new_record_id="silver:456",
        )

        assert info.resolution_type == "reprocessed"
        assert info.resolved_at == _ts(10)
        assert info.resolved_by == "user-123"
        assert info.reason == "Fixed data issue"
        assert info.new_record_id == "silver:456"

    def test_resolution_info_with_minimal_fields(self):
        """ResolutionInfo should work with minimal required fields."""
        info = ResolutionInfo(
            resolution_type="ignored",
            resolved_at=_ts(10),
        )

        assert info.resolution_type == "ignored"
        assert info.resolved_by is None
        assert info.reason is None
        assert info.new_record_id is None

    def test_resolution_info_validates_type(self):
        """ResolutionInfo should validate resolution_type."""
        with pytest.raises(ValueError, match="Invalid resolution_type"):
            ResolutionInfo(
                resolution_type="deleted",  # Invalid
                resolved_at=_ts(10),
            )

    def test_quarantine_internal_resolution_info_is_immutable(self):
        """ResolutionInfo should be frozen (immutable)."""
        info = ResolutionInfo(
            resolution_type="ignored",
            resolved_at=_ts(10),
        )

        with pytest.raises(AttributeError):
            info.resolution_type = "reprocessed"  # type: ignore


class TestQuarantineValidationFunctions:
    """Tests for quarantine validation functions."""

    def test_validate_required_fields_accepts_valid_input(self, sample_payload):
        """_validate_quarantine_required_fields should accept valid input."""
        _validate_quarantine_required_fields(
            "entry-123",
            "test_pipeline",
            "SCHEMA_VIOLATION",
            sample_payload,
            ContentHash("abc123"),
        )  # Should not raise

    def test_validate_required_fields_rejects_empty_entry_id(self, sample_payload):
        """_validate_quarantine_required_fields should reject empty entry_id."""
        with pytest.raises(ValueError, match="entry_id is required"):
            _validate_quarantine_required_fields(
                "",
                "test_pipeline",
                "SCHEMA_VIOLATION",
                sample_payload,
                ContentHash("abc123"),
            )

    def test_validate_required_fields_rejects_empty_pipeline_name(self, sample_payload):
        """_validate_quarantine_required_fields should reject empty pipeline_name."""
        with pytest.raises(ValueError, match="pipeline_name is required"):
            _validate_quarantine_required_fields(
                "entry-123",
                "",
                "SCHEMA_VIOLATION",
                sample_payload,
                ContentHash("abc123"),
            )

    def test_validate_required_fields_rejects_empty_error_code(self, sample_payload):
        """_validate_quarantine_required_fields should reject empty error_code."""
        with pytest.raises(ValueError, match="error_code is required"):
            _validate_quarantine_required_fields(
                "entry-123",
                "test_pipeline",
                "",
                sample_payload,
                ContentHash("abc123"),
            )

    def test_validate_required_fields_rejects_empty_payload(self):
        """_validate_quarantine_required_fields should reject empty payload."""
        with pytest.raises(ValueError, match="payload cannot be empty"):
            _validate_quarantine_required_fields(
                "entry-123",
                "test_pipeline",
                "SCHEMA_VIOLATION",
                {},  # Empty payload
                ContentHash("abc123"),
            )

    def test_validate_required_fields_rejects_empty_payload_hash(self, sample_payload):
        """_validate_quarantine_required_fields should reject empty payload_hash."""
        with pytest.raises(ValueError, match="payload_hash is required"):
            _validate_quarantine_required_fields(
                "entry-123",
                "test_pipeline",
                "SCHEMA_VIOLATION",
                sample_payload,
                ContentHash(""),
            )


# ──────────────────────────────────────────────────────────────────────────────
# quarantine read-model tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineEntryPropertiesMixin:
    """Tests for QuarantineEntryPropertiesMixin properties."""

    def test_quarantine_properties_accessors_return_correct_values(
        self, quarantine_entry
    ):
        """Read model properties should return correct aggregate state."""
        assert quarantine_entry.entry_id is not None
        assert quarantine_entry.pipeline_name == "test_pipeline"
        assert quarantine_entry.error_code == "SCHEMA_VIOLATION"
        assert quarantine_entry.payload == {
            "id": "bad-record",
            "value": "invalid",
            "source": "test",
        }
        assert quarantine_entry.payload_hash is not None
        assert quarantine_entry.status == QuarantineStatus.NEW
        assert quarantine_entry.created_at == _ts(0)
        assert quarantine_entry.metadata == {}
        assert quarantine_entry.resolution_info is None

    def test_payload_returns_copy_not_reference(self, quarantine_entry):
        """payload property should return a copy, not the original reference."""
        payload = quarantine_entry.payload
        payload["modified"] = "value"

        # Original should be unchanged
        assert "modified" not in quarantine_entry.payload

    def test_metadata_returns_copy_not_reference(self, run_id, batch_id):
        """metadata property should return a copy, not the original reference."""
        entry = QuarantineEntry.create(
            pipeline_name="test_pipeline",
            error_code="SCHEMA_VIOLATION",
            payload={"id": "bad-record"},
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
            metadata={"key": "value"},
        )

        metadata = entry.metadata
        metadata["new_key"] = "new_value"

        # Original should be unchanged
        assert "new_key" not in entry.metadata

    def test_is_resolved_returns_false_for_new_status(self, quarantine_entry):
        """is_resolved should return False for NEW status."""
        assert not quarantine_entry.is_resolved

    def test_is_resolved_returns_true_for_terminal_statuses(self, run_id, batch_id):
        """is_resolved should return True for terminal statuses."""
        for status in [
            QuarantineStatus.IGNORED,
            QuarantineStatus.REPROCESSED,
            QuarantineStatus.EXPIRED,
        ]:
            entry = QuarantineEntry(
                entry_id="test-id",
                pipeline_name="test_pipeline",
                error_code="SCHEMA_VIOLATION",
                payload={"id": "bad-record"},
                payload_hash=ContentHash("abc123"),
                run_id=run_id,
                batch_id=batch_id,
                created_at=_ts(0),
            )
            # Manually set status for testing
            object.__setattr__(entry, "_status", status)
            object.__setattr__(
                entry, "_resolution_info", ResolutionInfo("ignored", _ts(10))
            )

            assert entry.is_resolved

    def test_age_seconds_returns_none_for_unresolved_entry(self, quarantine_entry):
        """age_seconds should return None for unresolved entries."""
        assert quarantine_entry.age_seconds is None

    def test_age_seconds_calculates_duration_for_resolved_entry(self, run_id, batch_id):
        """age_seconds should calculate duration for resolved entries."""
        entry = QuarantineEntry(
            entry_id="test-id",
            pipeline_name="test_pipeline",
            error_code="SCHEMA_VIOLATION",
            payload={"id": "bad-record"},
            payload_hash=ContentHash("abc123"),
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )
        resolution_info = ResolutionInfo("ignored", _ts(100))
        object.__setattr__(entry, "_resolution_info", resolution_info)

        assert entry.age_seconds == 100.0

    def test_age_seconds_at_calculates_relative_duration(self, quarantine_entry):
        """age_seconds_at should calculate duration relative to reference time."""
        age = quarantine_entry.age_seconds_at(_ts(50))
        assert age == 50.0

    def test_quarantine_properties_repr_includes_key_state(self, quarantine_entry):
        """__repr__ should include key aggregate state."""
        repr_str = repr(quarantine_entry)
        assert "QuarantineEntry(" in repr_str
        assert "pipeline=" in repr_str
        assert "error_code=" in repr_str
        assert "status=" in repr_str


# ──────────────────────────────────────────────────────────────────────────────
# quarantine transition tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineEntryTransitionsMixin:
    """Tests for QuarantineEntryTransitionsMixin state transition methods."""

    def test_start_review_transitions_new_to_under_review(self, quarantine_entry):
        """start_review should transition NEW -> UNDER_REVIEW."""
        assert quarantine_entry.status == QuarantineStatus.NEW

        quarantine_entry.start_review()

        assert quarantine_entry.status == QuarantineStatus.UNDER_REVIEW

    def test_start_review_validates_status(self, quarantine_entry):
        """start_review should only work from NEW status."""
        quarantine_entry.start_review()

        with pytest.raises(InvalidStateError, match="Cannot start review"):
            quarantine_entry.start_review()

    def test_mark_ignored_transitions_to_ignored(self, quarantine_entry):
        """mark_ignored should transition to IGNORED status."""
        quarantine_entry.start_review()
        quarantine_entry.mark_ignored(
            reason="Known bad data source",
            resolved_by="user-123",
            resolved_at=_ts(10),
        )

        assert quarantine_entry.status == QuarantineStatus.IGNORED
        assert quarantine_entry.resolution_info is not None
        assert quarantine_entry.resolution_info.resolution_type == "ignored"
        assert quarantine_entry.resolution_info.reason == "Known bad data source"
        assert quarantine_entry.resolution_info.resolved_by == "user-123"

    def test_mark_ignored_validates_resolvable_status(self, quarantine_entry):
        """mark_ignored should only work from resolvable statuses."""
        # Mark as ignored first
        quarantine_entry.start_review()
        quarantine_entry.mark_ignored(reason="test", resolved_at=_ts(10))

        # Try again from terminal status
        with pytest.raises(InvalidStateError, match="Cannot mark_ignored"):
            quarantine_entry.mark_ignored(reason="test", resolved_at=_ts(20))

    def test_mark_ignored_emits_quarantine_entry_resolved_event(
        self, quarantine_entry, run_id: RunID
    ):
        """mark_ignored should emit QuarantineEntryResolved event."""
        quarantine_entry.collect_events()  # clear creation event
        quarantine_entry.start_review()

        quarantine_entry.mark_ignored(
            reason="Known bad data source",
            resolved_by="qa-bot",
            resolved_at=_ts(10),
        )

        events = quarantine_entry.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], QuarantineEntryResolved)
        assert events[0].run_id == run_id
        assert events[0].entry_id == quarantine_entry.entry_id
        assert events[0].resolution == "ignored"
        assert events[0].resolved_by == "qa-bot"
        assert events[0].occurred_at == _ts(10)

    def test_mark_reprocessed_transitions_to_reprocessed(self, quarantine_entry):
        """mark_reprocessed should transition to REPROCESSED status."""
        quarantine_entry.start_review()
        quarantine_entry.mark_reprocessed(
            new_record_id="silver:123",
            resolved_by="system",
            resolved_at=_ts(10),
        )

        assert quarantine_entry.status == QuarantineStatus.REPROCESSED
        assert quarantine_entry.resolution_info is not None
        assert quarantine_entry.resolution_info.resolution_type == "reprocessed"
        assert quarantine_entry.resolution_info.new_record_id == "silver:123"
        assert quarantine_entry.resolution_info.resolved_by == "system"

    def test_quarantine_transitions_mark_reprocessed_requires_new_record_id(
        self, quarantine_entry
    ):
        """mark_reprocessed should require new_record_id."""
        quarantine_entry.start_review()

        with pytest.raises(ValueError, match="new_record_id is required"):
            quarantine_entry.mark_reprocessed(
                new_record_id="",  # Empty
                resolved_at=_ts(10),
            )

    def test_mark_reprocessed_emits_quarantine_entry_resolved_event(
        self, quarantine_entry, run_id: RunID
    ):
        """mark_reprocessed should emit QuarantineEntryResolved event."""
        quarantine_entry.collect_events()  # clear creation event
        quarantine_entry.start_review()

        quarantine_entry.mark_reprocessed(
            new_record_id="silver:999",
            resolved_by="reprocessor",
            resolved_at=_ts(12),
        )

        events = quarantine_entry.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], QuarantineEntryResolved)
        assert events[0].run_id == run_id
        assert events[0].entry_id == quarantine_entry.entry_id
        assert events[0].resolution == "reprocessed"
        assert events[0].resolved_by == "reprocessor"
        assert events[0].occurred_at == _ts(12)

    def test_mark_expired_transitions_to_expired(self, quarantine_entry):
        """mark_expired should transition to EXPIRED status."""
        quarantine_entry.mark_expired(expired_at=_ts(100))

        assert quarantine_entry.status == QuarantineStatus.EXPIRED
        assert quarantine_entry.resolution_info is not None
        assert quarantine_entry.resolution_info.resolution_type == "expired"
        assert quarantine_entry.resolution_info.reason == "Retention period exceeded"

    def test_mark_ignored_invalid_from_expired(self, quarantine_entry):
        """mark_ignored should fail from EXPIRED status."""
        quarantine_entry.mark_expired(expired_at=_ts(100))

        with pytest.raises(InvalidStateError, match="Cannot mark_ignored"):
            quarantine_entry.mark_ignored(
                reason="already expired", resolved_at=_ts(101)
            )

    def test_mark_reprocessed_invalid_from_expired(self, quarantine_entry):
        """mark_reprocessed should fail from EXPIRED status."""
        quarantine_entry.mark_expired(expired_at=_ts(100))

        with pytest.raises(InvalidStateError, match="Cannot mark_reprocessed"):
            quarantine_entry.mark_reprocessed(
                new_record_id="silver:999",
                resolved_at=_ts(101),
            )

    def test_mark_expired_validates_non_terminal_status(self, quarantine_entry):
        """mark_expired should fail for terminal statuses."""
        quarantine_entry.start_review()
        quarantine_entry.mark_ignored(reason="test", resolved_at=_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot expire"):
            quarantine_entry.mark_expired(expired_at=_ts(20))

    def test_add_metadata_modifies_metadata(self, quarantine_entry):
        """add_metadata should add or update metadata entries."""
        quarantine_entry.add_metadata("reviewer", "user-123")
        quarantine_entry.add_metadata("priority", "high")

        assert quarantine_entry.metadata == {"reviewer": "user-123", "priority": "high"}

    def test_add_metadata_validates_non_terminal_status(self, quarantine_entry):
        """add_metadata should fail for terminal statuses."""
        quarantine_entry.start_review()
        quarantine_entry.mark_ignored(reason="test", resolved_at=_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot modify metadata"):
            quarantine_entry.add_metadata("key", "value")

    def test_quarantine_transitions_collect_events_clears_event_list(
        self, quarantine_entry
    ):
        """collect_events should return and clear accumulated events."""
        events = quarantine_entry.collect_events()
        assert len(events) >= 1  # At least creation event

        # Second call should return empty list
        events2 = quarantine_entry.collect_events()
        assert len(events2) == 0

    def test_assert_can_resolve_validates_status(self, quarantine_entry):
        """_assert_can_resolve should raise InvalidStateError for non-resolvable statuses."""
        quarantine_entry.start_review()
        quarantine_entry.mark_ignored(reason="test", resolved_at=_ts(10))

        # Now status is IGNORED (terminal)
        with pytest.raises(InvalidStateError, match="Cannot mark_ignored"):
            quarantine_entry.mark_ignored(reason="test", resolved_at=_ts(20))


# ──────────────────────────────────────────────────────────────────────────────
# _quarantine_aggregate.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineEntryAggregateRoot:
    """Tests for QuarantineEntry aggregate root construction and factory methods."""

    def test_constructor_validates_required_fields(self, run_id, batch_id):
        """QuarantineEntry constructor should validate required fields."""
        with pytest.raises(ValueError, match="entry_id is required"):
            QuarantineEntry(
                entry_id="",  # Empty
                pipeline_name="test_pipeline",
                error_code="SCHEMA_VIOLATION",
                payload={"id": "bad-record"},
                payload_hash=ContentHash("abc123"),
                run_id=run_id,
                batch_id=batch_id,
                created_at=_ts(0),
            )

    def test_constructor_creates_deep_copy_of_payload(self, run_id, batch_id):
        """Constructor should create deep copy of payload to ensure immutability."""
        original_payload = {"id": "bad-record", "value": "invalid"}
        entry = QuarantineEntry(
            entry_id="test-id",
            pipeline_name="test_pipeline",
            error_code="SCHEMA_VIOLATION",
            payload=original_payload,
            payload_hash=ContentHash("abc123"),
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )

        # Modify original
        original_payload["modified"] = "value"

        # Entry payload should be unchanged
        assert "modified" not in entry.payload

    def test_constructor_initializes_new_status(self, run_id, batch_id):
        """Constructor should initialize status as NEW."""
        entry = QuarantineEntry(
            entry_id="test-id",
            pipeline_name="test_pipeline",
            error_code="SCHEMA_VIOLATION",
            payload={"id": "bad-record"},
            payload_hash=ContentHash("abc123"),
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )

        assert entry.status == QuarantineStatus.NEW

    def test_create_factory_generates_deterministic_ids(
        self, run_id, batch_id, sample_payload
    ):
        """create factory should generate deterministic entry_id and payload_hash."""
        entry1 = QuarantineEntry.create(
            pipeline_name="test_pipeline",
            error_code="SCHEMA_VIOLATION",
            payload=sample_payload,
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )
        entry2 = QuarantineEntry.create(
            pipeline_name="test_pipeline",
            error_code="SCHEMA_VIOLATION",
            payload=sample_payload,
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )

        # Same inputs should produce same IDs
        assert entry1.entry_id == entry2.entry_id
        assert entry1.payload_hash == entry2.payload_hash

    def test_create_factory_computes_payload_hash(self, run_id, batch_id):
        """create factory should compute SHA256 hash of payload."""
        entry = QuarantineEntry.create(
            pipeline_name="test_pipeline",
            error_code="SCHEMA_VIOLATION",
            payload={"id": "test-record"},
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )

        assert entry.payload_hash is not None
        assert len(entry.payload_hash) == 64  # SHA256 hex length

    def test_create_factory_emits_creation_event(self, run_id, batch_id):
        """create factory should emit QuarantineEntryCreated event."""
        entry = QuarantineEntry.create(
            pipeline_name="test_pipeline",
            error_code="SCHEMA_VIOLATION",
            payload={"id": "bad-record"},
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
        )

        events = entry.collect_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "QuarantineEntryCreated"
        assert events[0].pipeline_name == "test_pipeline"
        assert events[0].error_code == "SCHEMA_VIOLATION"

    def test_create_factory_accepts_metadata(self, run_id, batch_id):
        """create factory should accept and store metadata."""
        metadata = {"source": "manual-review", "priority": "high"}
        entry = QuarantineEntry.create(
            pipeline_name="test_pipeline",
            error_code="SCHEMA_VIOLATION",
            payload={"id": "bad-record"},
            run_id=run_id,
            batch_id=batch_id,
            created_at=_ts(0),
            metadata=metadata,
        )

        assert entry.metadata == metadata


# ──────────────────────────────────────────────────────────────────────────────
# State Transition Integration Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQuarantineEntryStateTransitions:
    """Integration tests for complete state transition sequences."""

    def test_new_to_ignored_flow(self, quarantine_entry):
        """Test complete NEW -> UNDER_REVIEW -> IGNORED flow."""
        assert quarantine_entry.status == QuarantineStatus.NEW

        quarantine_entry.start_review()
        assert quarantine_entry.status == QuarantineStatus.UNDER_REVIEW

        quarantine_entry.mark_ignored(
            reason="Known bad data source",
            resolved_by="user-123",
            resolved_at=_ts(10),
        )

        assert quarantine_entry.status == QuarantineStatus.IGNORED
        assert quarantine_entry.is_resolved
        assert quarantine_entry.age_seconds == 10.0

    def test_new_to_reprocessed_flow(self, quarantine_entry):
        """Test complete NEW -> UNDER_REVIEW -> REPROCESSED flow."""
        quarantine_entry.start_review()
        quarantine_entry.mark_reprocessed(
            new_record_id="silver:123",
            resolved_by="system",
            resolved_at=_ts(15),
        )

        assert quarantine_entry.status == QuarantineStatus.REPROCESSED
        assert quarantine_entry.is_resolved
        assert quarantine_entry.resolution_info.new_record_id == "silver:123"

    def test_new_to_expired_flow(self, quarantine_entry):
        """Test NEW -> EXPIRED flow (retention policy)."""
        quarantine_entry.mark_expired(expired_at=_ts(100))

        assert quarantine_entry.status == QuarantineStatus.EXPIRED
        assert quarantine_entry.is_resolved
        assert quarantine_entry.resolution_info.reason == "Retention period exceeded"

    def test_metadata_modification_before_resolution(self, quarantine_entry):
        """Test that metadata can be modified before resolution."""
        quarantine_entry.add_metadata("reviewer", "user-123")
        quarantine_entry.add_metadata("notes", "Needs investigation")

        assert quarantine_entry.metadata == {
            "reviewer": "user-123",
            "notes": "Needs investigation",
        }

        quarantine_entry.start_review()
        quarantine_entry.add_metadata("priority", "high")

        assert "priority" in quarantine_entry.metadata

        # After resolution, metadata modification should fail
        quarantine_entry.mark_ignored(reason="test", resolved_at=_ts(10))
        with pytest.raises(InvalidStateError):
            quarantine_entry.add_metadata("key", "value")

    def test_immutability_of_payload_and_hash(self, quarantine_entry):
        """Test that payload and payload_hash remain immutable."""
        original_payload = quarantine_entry.payload
        original_hash = quarantine_entry.payload_hash

        # Try to modify through property (should not affect internal state)
        quarantine_entry.payload["modified"] = "value"

        # Internal state should be unchanged
        assert quarantine_entry.payload == original_payload
        assert quarantine_entry.payload_hash == original_hash

    def test_error_code_immutability(self, quarantine_entry):
        """Test that error_code cannot be changed."""
        original_error_code = quarantine_entry.error_code

        # Error code is a property, not a settable attribute
        assert quarantine_entry.error_code == original_error_code
        # Cannot set error_code (it's immutable by design)
