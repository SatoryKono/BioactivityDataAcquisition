"""Unit tests for CompositeCheckpointState.

Tests for checkpoint state serialization, deserialization, and state mutations.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.domain.composite.result import (
    EnrichmentResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from tests.helpers.clock import FixedClock


_FIXED_CLOCK = FixedClock(datetime(2026, 5, 22, 12, 0, tzinfo=UTC))


class TestCompositeCheckpointStateCreation:
    """Tests for CompositeCheckpointState creation."""

    def test_default_state_is_not_started(self):
        """Default FSM state should be NOT_STARTED."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
        )
        assert state.state == CompositePipelineState.NOT_STARTED

    def test_explicit_state_is_preserved(self):
        """Explicitly set state should be preserved."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.ENRICHING,
        )
        assert state.state == CompositePipelineState.ENRICHING

    def test_frozen_dataclass(self):
        """State should be immutable (frozen)."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
        )
        with pytest.raises(AttributeError):
            state.state = CompositePipelineState.COMPLETED  # type: ignore[misc]


class TestWithSeedCompleted:
    """Tests for with_seed_completed method."""

    def test_sets_seed_completed_flag(self):
        """with_seed_completed should set seed_completed=True."""
        initial = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
        )
        seed_result = SeedResult(
            pipeline_name="chembl_activity",
            records_extracted=100,
            records_silver=95,
            keys_generated=90,
            duration_seconds=10.5,
        )
        updated = initial.with_seed_completed(seed_result, clock=_FIXED_CLOCK)
        assert updated.seed_completed is True
        assert updated.seed_result == seed_result

    def test_sets_state_to_seed_completed(self):
        """with_seed_completed should set state to SEED_COMPLETED."""
        initial = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.SEED_RUNNING,
        )
        seed_result = SeedResult(
            pipeline_name="chembl_activity",
            records_extracted=100,
            records_silver=95,
            keys_generated=90,
            duration_seconds=10.5,
        )
        updated = initial.with_seed_completed(seed_result, clock=_FIXED_CLOCK)
        assert updated.state == CompositePipelineState.SEED_COMPLETED

    def test_preserves_other_fields(self):
        """with_seed_completed should preserve other fields."""
        created_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        initial = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            created_at=created_at,
        )
        seed_result = SeedResult(
            pipeline_name="chembl_activity",
            records_extracted=100,
            records_silver=95,
            keys_generated=90,
            duration_seconds=10.5,
        )
        updated = initial.with_seed_completed(seed_result, clock=_FIXED_CLOCK)
        assert updated.composite_name == "test_composite"
        assert updated.run_id == "run-123"
        assert updated.created_at == created_at

    def test_updates_timestamp(self):
        """with_seed_completed should update updated_at."""
        initial = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
        )
        seed_result = SeedResult(
            pipeline_name="chembl_activity",
            records_extracted=100,
            records_silver=95,
            keys_generated=90,
            duration_seconds=10.5,
        )
        updated = initial.with_seed_completed(seed_result, clock=_FIXED_CLOCK)
        assert updated.updated_at is not None


class TestWithEnricherCompleted:
    """Tests for with_enricher_completed method."""

    def test_adds_enricher_to_completed_set__test_with_enricher_completed_application_composite_test_checkpoint_131(
        self,
    ):
        """with_enricher_completed should add enricher to completed_enrichers."""
        initial = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.SEED_COMPLETED,
        )
        result = EnrichmentResult.success(
            enricher_name="crossref",
            records_input=100,
            records_enriched=95,
            records_not_found=5,
            duration_seconds=10.5,
        )
        updated = initial.with_enricher_completed(
            "crossref",
            result,
            clock=_FIXED_CLOCK,
        )
        assert "crossref" in updated.completed_enrichers
        assert updated.enrichment_results["crossref"] == result

    def test_sets_state_to_enriching(self):
        """with_enricher_completed should set state to ENRICHING."""
        initial = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.SEED_COMPLETED,
        )
        result = EnrichmentResult.success(
            enricher_name="crossref",
            records_input=100,
            records_enriched=95,
            records_not_found=5,
            duration_seconds=10.5,
        )
        updated = initial.with_enricher_completed(
            "crossref",
            result,
            clock=_FIXED_CLOCK,
        )
        assert updated.state == CompositePipelineState.ENRICHING

    def test_accumulates_multiple_enrichers__test_with_enricher_completed_application_composite_test_checkpoint_174(
        self,
    ):
        """Multiple with_enricher_completed calls should accumulate."""
        initial = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.SEED_COMPLETED,
        )
        result1 = EnrichmentResult.success(
            enricher_name="crossref",
            records_input=100,
            records_enriched=95,
            records_not_found=5,
            duration_seconds=10.5,
        )
        result2 = EnrichmentResult.success(
            enricher_name="pubmed",
            records_input=100,
            records_enriched=80,
            records_not_found=20,
            duration_seconds=15.0,
        )
        updated1 = initial.with_enricher_completed(
            "crossref",
            result1,
            clock=_FIXED_CLOCK,
        )
        updated2 = updated1.with_enricher_completed(
            "pubmed",
            result2,
            clock=_FIXED_CLOCK,
        )
        assert updated2.completed_enrichers == frozenset({"crossref", "pubmed"})
        assert len(updated2.enrichment_results) == 2

    def test_preserves_seed_result(self):
        """with_enricher_completed should preserve seed_result."""
        seed_result = SeedResult(
            pipeline_name="chembl_activity",
            records_extracted=100,
            records_silver=95,
            keys_generated=90,
            duration_seconds=10.5,
        )
        initial = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            seed_completed=True,
            seed_result=seed_result,
        )
        enricher_result = EnrichmentResult.success(
            enricher_name="crossref",
            records_input=100,
            records_enriched=95,
            records_not_found=5,
            duration_seconds=10.5,
        )
        updated = initial.with_enricher_completed(
            "crossref",
            enricher_result,
            clock=_FIXED_CLOCK,
        )
        assert updated.seed_completed is True
        assert updated.seed_result == seed_result


class TestWithState:
    """Tests for with_state method."""

    def test_updates_state(self):
        """with_state should update FSM state."""
        initial = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.ENRICHING,
        )
        updated = initial.with_state(
            CompositePipelineState.ENRICHMENT_COMPLETED,
            clock=_FIXED_CLOCK,
        )
        assert updated.state == CompositePipelineState.ENRICHMENT_COMPLETED

    def test_preserves_all_other_fields(self):
        """with_state should preserve all other fields."""
        seed_result = SeedResult(
            pipeline_name="chembl_activity",
            records_extracted=100,
            records_silver=95,
            keys_generated=90,
            duration_seconds=10.5,
        )
        enricher_result = EnrichmentResult.success(
            enricher_name="crossref",
            records_input=100,
            records_enriched=95,
            records_not_found=5,
            duration_seconds=10.5,
        )
        created_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        initial = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            seed_result=seed_result,
            completed_enrichers=frozenset({"crossref"}),
            enrichment_results={"crossref": enricher_result},
            created_at=created_at,
        )
        updated = initial.with_state(
            CompositePipelineState.MERGING,
            clock=_FIXED_CLOCK,
        )
        assert updated.composite_name == initial.composite_name
        assert updated.run_id == initial.run_id
        assert updated.seed_completed == initial.seed_completed
        assert updated.seed_result == initial.seed_result
        assert updated.completed_enrichers == initial.completed_enrichers
        assert updated.enrichment_results == initial.enrichment_results
        assert updated.created_at == initial.created_at

    def test_can_set_to_failed(self):
        """with_state should allow setting FAILED state."""
        initial = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.ENRICHING,
        )
        updated = initial.with_state(
            CompositePipelineState.FAILED,
            clock=_FIXED_CLOCK,
        )
        assert updated.state == CompositePipelineState.FAILED

    def test_updates_timestamp(self):
        """with_state should update updated_at."""
        initial = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
        )
        updated = initial.with_state(
            CompositePipelineState.SEED_RUNNING,
            clock=_FIXED_CLOCK,
        )
        assert updated.updated_at is not None


class TestIsResumable:
    """Tests for is_resumable property."""

    def test_resumable_when_seed_completed(self):
        """Checkpoint should be resumable when seed is completed."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            seed_completed=True,
        )
        assert state.is_resumable is True

    def test_resumable_when_enrichers_completed(self):
        """Checkpoint should be resumable when enrichers are completed."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            completed_enrichers=frozenset({"crossref"}),
        )
        assert state.is_resumable is True

    def test_resumable_based_on_fsm_state(self):
        """Checkpoint should be resumable based on FSM state."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.SEED_COMPLETED,
        )
        assert state.is_resumable is True

    def test_not_resumable_when_fresh(self):
        """Fresh checkpoint should not be resumable."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
        )
        assert state.is_resumable is False

    def test_resumable_when_failed_with_progress(self):
        """Checkpoint in FAILED state should be resumable if progress was made."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.FAILED,
            seed_completed=True,
        )
        assert state.is_resumable is True

    def test_resumable_based_on_failed_fsm_state(self):
        """FAILED state should be resumable via FSM state check."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.FAILED,
        )
        # FAILED is now resumable to allow merge retry
        assert state.is_resumable is True


class TestSerialization:
    """Tests for to_dict and from_dict methods."""

    def test_roundtrip_with_all_states(self):
        """Serialization roundtrip should preserve all states."""
        for fsm_state in CompositePipelineState:
            original = CompositeCheckpointState(
                composite_name="test_composite",
                run_id="run-123",
                state=fsm_state,
            )
            serialized = original.to_dict()
            restored = CompositeCheckpointState.from_dict(serialized)
            assert restored.state == fsm_state

    def test_to_dict_includes_state(self):
        """to_dict should include state field."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.ENRICHING,
        )
        data = state.to_dict()
        assert "state" in data
        assert data["state"] == "enriching"

    def test_full_roundtrip(self):
        """Full roundtrip should preserve all fields."""
        seed_result = SeedResult(
            pipeline_name="chembl_activity",
            records_extracted=100,
            records_silver=95,
            keys_generated=90,
            duration_seconds=10.5,
        )
        enricher_result = EnrichmentResult.success(
            enricher_name="crossref",
            records_input=100,
            records_enriched=95,
            records_not_found=5,
            duration_seconds=10.5,
        )
        created_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        updated_at = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)
        original = CompositeCheckpointState(
            composite_name="test_composite",
            run_id="run-123",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            seed_result=seed_result,
            completed_enrichers=frozenset({"crossref"}),
            enrichment_results={"crossref": enricher_result},
            created_at=created_at,
            updated_at=updated_at,
        )
        serialized = original.to_dict()
        restored = CompositeCheckpointState.from_dict(serialized)
        assert restored.composite_name == original.composite_name
        assert restored.run_id == original.run_id
        assert restored.state == original.state
        assert restored.seed_completed == original.seed_completed
        assert restored.seed_result.pipeline_name == original.seed_result.pipeline_name
        assert restored.completed_enrichers == original.completed_enrichers
        assert "crossref" in restored.enrichment_results
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at


class TestBackwardCompatibility:
    """Tests for backward compatibility with old checkpoints."""

    def test_missing_state_defaults_to_not_started(self):
        """Old checkpoint without state field should default to NOT_STARTED."""
        old_data = {
            "composite_name": "test_composite",
            "run_id": "run-123",
            "seed_completed": False,
            "seed_result": None,
            "completed_enrichers": [],
            "enrichment_results": {},
            "created_at": "2024-01-15T10:30:00+00:00",
            "updated_at": "2024-01-15T11:00:00+00:00",
        }
        restored = CompositeCheckpointState.from_dict(old_data)
        assert restored.state == CompositePipelineState.NOT_STARTED

    def test_old_checkpoint_with_seed_completed(self):
        """Old checkpoint with seed_completed should still work."""
        old_data = {
            "composite_name": "test_composite",
            "run_id": "run-123",
            "seed_completed": True,
            "seed_result": {
                "pipeline_name": "chembl_activity",
                "records_extracted": 100,
                "records_silver": 95,
                "keys_generated": 90,
                "duration_seconds": 10.5,
                "resumed": False,
            },
            "completed_enrichers": ["crossref"],
            "enrichment_results": {
                "crossref": {
                    "enricher_name": "crossref",
                    "status": "success",
                    "records_input": 100,
                    "records_enriched": 95,
                    "records_not_found": 5,
                    "records_errored": 0,
                    "dq_error_rate": 0.0,
                    "duration_seconds": 10.5,
                    "error_message": None,
                }
            },
            "created_at": "2024-01-15T10:30:00+00:00",
            "updated_at": "2024-01-15T11:00:00+00:00",
        }
        restored = CompositeCheckpointState.from_dict(old_data)
        assert restored.state == CompositePipelineState.NOT_STARTED
        assert restored.seed_completed is True
        assert restored.is_resumable is True


class TestCorruptedStateHandling:
    """Tests for handling corrupted state values."""

    def test_invalid_state_value_defaults_to_not_started(self):
        """Corrupted state value should default to NOT_STARTED."""
        corrupted_data = {
            "composite_name": "test_composite",
            "run_id": "run-123",
            "state": "INVALID_STATE",
            "seed_completed": False,
            "seed_result": None,
            "completed_enrichers": [],
            "enrichment_results": {},
            "created_at": "2024-01-15T10:30:00+00:00",
            "updated_at": "2024-01-15T11:00:00+00:00",
        }
        # Should not raise, should return NOT_STARTED
        restored = CompositeCheckpointState.from_dict(corrupted_data)
        assert restored.state == CompositePipelineState.NOT_STARTED

    def test_empty_string_state_defaults_to_not_started(self):
        """Empty string state should default to NOT_STARTED."""
        corrupted_data = {
            "composite_name": "test_composite",
            "run_id": "run-123",
            "state": "",
            "seed_completed": False,
            "seed_result": None,
            "completed_enrichers": [],
            "enrichment_results": {},
        }
        restored = CompositeCheckpointState.from_dict(corrupted_data)
        assert restored.state == CompositePipelineState.NOT_STARTED

    def test_none_state_defaults_to_not_started(self):
        """Explicit None state should default to NOT_STARTED."""
        data = {
            "composite_name": "test_composite",
            "run_id": "run-123",
            "state": None,
            "seed_completed": False,
            "seed_result": None,
            "completed_enrichers": [],
            "enrichment_results": {},
        }
        restored = CompositeCheckpointState.from_dict(data)
        assert restored.state == CompositePipelineState.NOT_STARTED
