"""Unit tests for CompositeCheckpointState.

Covers immutable state transitions, is_resumable property,
to_dict / from_dict round-trip, backward-compatibility, and
error-recovery paths.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_seed_result(
    pipeline_name: str = "chembl_activity",
    records_extracted: int = 100,
    records_silver: int = 95,
    keys_generated: int = 90,
    duration_seconds: float = 10.5,
    resumed: bool = False,
) -> SeedResult:
    return SeedResult(
        pipeline_name=pipeline_name,
        records_extracted=records_extracted,
        records_silver=records_silver,
        keys_generated=keys_generated,
        duration_seconds=duration_seconds,
        resumed=resumed,
    )


def _make_dependency_result(
    pipeline_name: str = "uniprot",
    status: DependencyStatus = DependencyStatus.SUCCESS,
    records_extracted: int = 50,
    records_silver: int = 48,
    duration_seconds: float = 5.0,
    error_message: str | None = None,
    resumed: bool = False,
) -> DependencyResult:
    return DependencyResult(
        pipeline_name=pipeline_name,
        status=status,
        records_extracted=records_extracted,
        records_silver=records_silver,
        duration_seconds=duration_seconds,
        error_message=error_message,
        resumed=resumed,
    )


def _make_enrichment_result(
    enricher_name: str = "crossref",
    status: EnrichmentStatus = EnrichmentStatus.SUCCESS,
    records_input: int = 100,
    records_enriched: int = 95,
    records_not_found: int = 5,
    records_errored: int = 0,
    dq_error_rate: float = 0.0,
    duration_seconds: float = 10.5,
    error_message: str | None = None,
) -> EnrichmentResult:
    return EnrichmentResult(
        enricher_name=enricher_name,
        status=status,
        records_input=records_input,
        records_enriched=records_enriched,
        records_not_found=records_not_found,
        records_errored=records_errored,
        dq_error_rate=dq_error_rate,
        duration_seconds=duration_seconds,
        error_message=error_message,
    )


# ---------------------------------------------------------------------------
# 1. Default state creation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDefaultStateCreation:
    """Tests for CompositeCheckpointState default values."""

    def test_default_fsm_state_is_not_started(self) -> None:
        """Default state should be NOT_STARTED."""
        state = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
        )
        assert state.state == CompositePipelineState.NOT_STARTED

    def test_default_seed_completed_is_false(self) -> None:
        """Default seed_completed should be False."""
        state = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
        )
        assert state.seed_completed is False

    def test_default_seed_result_is_none(self) -> None:
        """Default seed_result should be None."""
        state = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
        )
        assert state.seed_result is None

    def test_default_completed_dependencies_is_empty(self) -> None:
        """Default completed_dependencies should be an empty frozenset."""
        state = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
        )
        assert state.completed_dependencies == frozenset()

    def test_default_completed_enrichers_is_empty(self) -> None:
        """Default completed_enrichers should be an empty frozenset."""
        state = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
        )
        assert state.completed_enrichers == frozenset()

    def test_composite_name_and_run_id_stored(self) -> None:
        """composite_name and run_id should be stored verbatim."""
        state = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-abc-123",
        )
        assert state.composite_name == "my_composite"
        assert state.run_id == "run-abc-123"

    def test_default_replay_watermark_is_empty(self) -> None:
        """Replay watermark fields default to None for fresh snapshots."""
        state = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
        )
        assert state.last_event_id is None
        assert state.last_event_occurred_at is None


# ---------------------------------------------------------------------------
# 2. with_seed_completed
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWithSeedCompleted:
    """Tests for with_seed_completed transition method."""

    def test_sets_seed_completed_true(self) -> None:
        """with_seed_completed sets seed_completed=True."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        result = initial.with_seed_completed(_make_seed_result())
        assert result.seed_completed is True

    def test_stores_seed_result(self) -> None:
        """with_seed_completed stores the provided SeedResult."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        seed = _make_seed_result(records_extracted=200, records_silver=180)
        updated = initial.with_seed_completed(seed)
        assert updated.seed_result is seed

    def test_sets_state_to_seed_completed(self) -> None:
        """FSM state transitions to SEED_COMPLETED."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        updated = initial.with_seed_completed(_make_seed_result())
        assert updated.state == CompositePipelineState.SEED_COMPLETED

    def test_preserves_composite_name_and_run_id(self) -> None:
        """Immutable fields composite_name and run_id are preserved."""
        initial = CompositeCheckpointState(composite_name="comp", run_id="run-42")
        updated = initial.with_seed_completed(_make_seed_result())
        assert updated.composite_name == "comp"
        assert updated.run_id == "run-42"

    def test_preserves_created_at(self) -> None:
        """created_at timestamp is carried over unchanged."""
        created = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
        initial = CompositeCheckpointState(
            composite_name="c", run_id="r", created_at=created
        )
        updated = initial.with_seed_completed(_make_seed_result())
        assert updated.created_at == created

    def test_sets_updated_at(self) -> None:
        """updated_at is set to a non-None datetime."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        updated = initial.with_seed_completed(_make_seed_result())
        assert updated.updated_at is not None

    def test_preserves_completed_enrichers(self) -> None:
        """Existing completed_enrichers are not reset."""
        initial = CompositeCheckpointState(
            composite_name="c",
            run_id="r",
            completed_enrichers=frozenset({"crossref"}),
        )
        updated = initial.with_seed_completed(_make_seed_result())
        assert "crossref" in updated.completed_enrichers


# ---------------------------------------------------------------------------
# 3. with_dependency_completed
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWithDependencyCompleted:
    """Tests for with_dependency_completed transition method."""

    def test_adds_dependency_to_completed_set(self) -> None:
        """with_dependency_completed adds the name to completed_dependencies."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        dep = _make_dependency_result(pipeline_name="uniprot")
        updated = initial.with_dependency_completed("uniprot", dep)
        assert "uniprot" in updated.completed_dependencies

    def test_stores_dependency_result(self) -> None:
        """with_dependency_completed stores result in dependency_results dict."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        dep = _make_dependency_result(pipeline_name="uniprot")
        updated = initial.with_dependency_completed("uniprot", dep)
        assert updated.dependency_results["uniprot"] is dep

    def test_sets_state_to_dependencies_running(self) -> None:
        """FSM state transitions to DEPENDENCIES_RUNNING."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        updated = initial.with_dependency_completed("dep1", _make_dependency_result())
        assert updated.state == CompositePipelineState.DEPENDENCIES_RUNNING

    def test_accumulates_multiple_dependencies(self) -> None:
        """Multiple calls accumulate entries in completed_dependencies."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        dep1 = _make_dependency_result(pipeline_name="uniprot")
        dep2 = _make_dependency_result(pipeline_name="chebi")

        updated1 = initial.with_dependency_completed("uniprot", dep1)
        updated2 = updated1.with_dependency_completed("chebi", dep2)

        assert updated2.completed_dependencies == frozenset({"uniprot", "chebi"})
        assert len(updated2.dependency_results) == 2

    def test_original_state_not_mutated(self) -> None:
        """Original state is not changed after transition."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        _ = initial.with_dependency_completed("dep", _make_dependency_result())
        assert initial.completed_dependencies == frozenset()


# ---------------------------------------------------------------------------
# 4. with_enricher_completed
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWithEnricherCompleted:
    """Tests for with_enricher_completed transition method."""

    def test_adds_enricher_to_completed_set(self) -> None:
        """with_enricher_completed adds enricher name to completed_enrichers."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        er = _make_enrichment_result(enricher_name="crossref")
        updated = initial.with_enricher_completed("crossref", er)
        assert "crossref" in updated.completed_enrichers

    def test_stores_enrichment_result(self) -> None:
        """with_enricher_completed stores result in enrichment_results."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        er = _make_enrichment_result(enricher_name="crossref")
        updated = initial.with_enricher_completed("crossref", er)
        assert updated.enrichment_results["crossref"] is er

    def test_sets_state_to_enriching(self) -> None:
        """FSM state transitions to ENRICHING."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        updated = initial.with_enricher_completed("e1", _make_enrichment_result())
        assert updated.state == CompositePipelineState.ENRICHING

    def test_accumulates_multiple_enrichers(self) -> None:
        """Multiple calls accumulate all enrichers in completed_enrichers."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        er1 = _make_enrichment_result(enricher_name="crossref")
        er2 = _make_enrichment_result(enricher_name="pubmed")

        updated = initial.with_enricher_completed(
            "crossref", er1
        ).with_enricher_completed("pubmed", er2)

        assert updated.completed_enrichers == frozenset({"crossref", "pubmed"})
        assert len(updated.enrichment_results) == 2

    def test_preserves_seed_completed(self) -> None:
        """seed_completed flag is not reset by with_enricher_completed."""
        initial = CompositeCheckpointState(
            composite_name="c", run_id="r", seed_completed=True
        )
        updated = initial.with_enricher_completed("e1", _make_enrichment_result())
        assert updated.seed_completed is True

    def test_original_state_not_mutated(self) -> None:
        """Original state is not changed after transition."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        _ = initial.with_enricher_completed("e1", _make_enrichment_result())
        assert initial.completed_enrichers == frozenset()


# ---------------------------------------------------------------------------
# 5. with_state
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWithState:
    """Tests for with_state transition method."""

    def test_updates_fsm_state(self) -> None:
        """with_state replaces the FSM state field."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        updated = initial.with_state(CompositePipelineState.MERGING)
        assert updated.state == CompositePipelineState.MERGING

    def test_preserves_all_other_fields(self) -> None:
        """with_state preserves seed_completed, enrichers, created_at, etc."""
        created = datetime(2024, 6, 1, tzinfo=UTC)
        enricher = _make_enrichment_result()
        initial = CompositeCheckpointState(
            composite_name="my_comp",
            run_id="run-99",
            seed_completed=True,
            seed_result=_make_seed_result(),
            completed_enrichers=frozenset({"crossref"}),
            enrichment_results={"crossref": enricher},
            created_at=created,
        )
        updated = initial.with_state(CompositePipelineState.ENRICHMENT_COMPLETED)

        assert updated.composite_name == "my_comp"
        assert updated.run_id == "run-99"
        assert updated.seed_completed is True
        assert updated.completed_enrichers == frozenset({"crossref"})
        assert updated.created_at == created

    def test_sets_updated_at(self) -> None:
        """with_state sets a non-None updated_at."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        updated = initial.with_state(CompositePipelineState.FAILED)
        assert updated.updated_at is not None

    def test_can_transition_to_failed(self) -> None:
        """with_state allows any FSM state value including FAILED."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        updated = initial.with_state(CompositePipelineState.FAILED)
        assert updated.state == CompositePipelineState.FAILED


# ---------------------------------------------------------------------------
# 6. is_resumable
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsResumable:
    """Tests for the is_resumable property."""

    def test_resumable_when_fsm_state_is_resumable(self) -> None:
        """is_resumable is True when state.is_resumable is True (SEED_COMPLETED)."""
        state = CompositeCheckpointState(
            composite_name="c",
            run_id="r",
            state=CompositePipelineState.SEED_COMPLETED,
        )
        assert state.is_resumable is True

    def test_resumable_when_failed_state(self) -> None:
        """FAILED state is resumable per CompositePipelineState.is_resumable."""
        state = CompositeCheckpointState(
            composite_name="c",
            run_id="r",
            state=CompositePipelineState.FAILED,
        )
        assert state.is_resumable is True

    def test_resumable_when_seed_completed_true_even_if_not_started(self) -> None:
        """Fallback: seed_completed=True makes is_resumable True even if FSM is NOT_STARTED."""
        state = CompositeCheckpointState(
            composite_name="c",
            run_id="r",
            state=CompositePipelineState.NOT_STARTED,
            seed_completed=True,
        )
        assert state.is_resumable is True

    def test_resumable_when_completed_enrichers_nonempty(self) -> None:
        """Fallback: non-empty completed_enrichers makes is_resumable True."""
        state = CompositeCheckpointState(
            composite_name="c",
            run_id="r",
            state=CompositePipelineState.NOT_STARTED,
            completed_enrichers=frozenset({"crossref"}),
        )
        assert state.is_resumable is True

    def test_not_resumable_for_fresh_not_started_state(self) -> None:
        """Fresh NOT_STARTED state with no progress is not resumable."""
        state = CompositeCheckpointState(composite_name="c", run_id="r")
        assert state.is_resumable is False

    def test_not_resumable_for_completed_terminal_state(self) -> None:
        """COMPLETED is terminal but not in the resumable set."""
        state = CompositeCheckpointState(
            composite_name="c",
            run_id="r",
            state=CompositePipelineState.COMPLETED,
        )
        # COMPLETED is not in is_resumable set; seed_completed=False; enrichers empty
        assert state.is_resumable is False


# ---------------------------------------------------------------------------
# 7. to_dict serialization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestToDict:
    """Tests for to_dict serialization."""

    def test_serializes_all_top_level_keys(self) -> None:
        """to_dict includes every expected key."""
        state = CompositeCheckpointState(composite_name="c", run_id="r")
        d = state.to_dict()
        expected_keys = {
            "composite_name",
            "run_id",
            "state",
            "seed_completed",
            "seed_result",
            "completed_dependencies",
            "dependency_results",
            "completed_enrichers",
            "enrichment_results",
            "merge_completed",
            "merge_result",
            "checkpoint_schema_version",
            "effective_config_hash",
            "contract_ref",
            "contract_version",
            "manifest_id",
            "composite_run_identity",
            "last_event_id",
            "last_event_occurred_at",
            "created_at",
            "updated_at",
        }
        assert expected_keys == set(d.keys())

    def test_state_serialized_as_string_value(self) -> None:
        """FSM state serialized as its StrEnum value."""
        state = CompositeCheckpointState(
            composite_name="c",
            run_id="r",
            state=CompositePipelineState.ENRICHING,
        )
        assert state.to_dict()["state"] == "enriching"

    def test_none_seed_result_serializes_as_none(self) -> None:
        """seed_result=None should produce None in the dict."""
        state = CompositeCheckpointState(composite_name="c", run_id="r")
        assert state.to_dict()["seed_result"] is None

    def test_seed_result_serializes_fields(self) -> None:
        """SeedResult fields are included in the nested dict."""
        seed = _make_seed_result(
            pipeline_name="chembl_activity",
            records_extracted=100,
            records_silver=95,
            keys_generated=90,
            duration_seconds=10.5,
            resumed=False,
        )
        state = CompositeCheckpointState(
            composite_name="c", run_id="r", seed_result=seed
        )
        d = state.to_dict()["seed_result"]
        assert isinstance(d, dict)
        assert d["pipeline_name"] == "chembl_activity"
        assert d["records_extracted"] == 100
        assert d["records_silver"] == 95
        assert d["keys_generated"] == 90
        assert d["duration_seconds"] == pytest.approx(10.5)
        assert d["resumed"] is False

    def test_dependency_results_serialized(self) -> None:
        """dependency_results are included with status as string."""
        dep = _make_dependency_result(
            pipeline_name="uniprot",
            status=DependencyStatus.FAILED,
            error_message="oops",
        )
        state = CompositeCheckpointState(
            composite_name="c",
            run_id="r",
            completed_dependencies=frozenset({"uniprot"}),
            dependency_results={"uniprot": dep},
        )
        d = state.to_dict()
        assert "uniprot" in d["dependency_results"]
        assert d["dependency_results"]["uniprot"]["status"] == "failed"
        assert d["dependency_results"]["uniprot"]["error_message"] == "oops"

    def test_enrichment_results_serialized(self) -> None:
        """enrichment_results are included with status as string."""
        er = _make_enrichment_result(
            enricher_name="crossref",
            status=EnrichmentStatus.PARTIAL,
            records_input=100,
            records_enriched=60,
        )
        state = CompositeCheckpointState(
            composite_name="c",
            run_id="r",
            completed_enrichers=frozenset({"crossref"}),
            enrichment_results={"crossref": er},
        )
        d = state.to_dict()
        assert "crossref" in d["enrichment_results"]
        assert d["enrichment_results"]["crossref"]["status"] == "partial"
        assert d["enrichment_results"]["crossref"]["records_enriched"] == 60

    def test_datetimes_serialized_as_isoformat(self) -> None:
        """created_at, updated_at, and watermark timestamps serialize as ISO-8601."""
        dt = datetime(2024, 3, 15, 9, 30, 0, tzinfo=UTC)
        state = CompositeCheckpointState(
            composite_name="c",
            run_id="r",
            last_event_id="evt-123",
            last_event_occurred_at=dt,
            created_at=dt,
            updated_at=dt,
        )
        d = state.to_dict()
        assert d["last_event_id"] == "evt-123"
        assert d["last_event_occurred_at"] == dt.isoformat()
        assert d["created_at"] == dt.isoformat()
        assert d["updated_at"] == dt.isoformat()

    def test_none_datetimes_serialized_as_none(self) -> None:
        """None timestamps and watermark fields produce None in the dict."""
        state = CompositeCheckpointState(composite_name="c", run_id="r")
        d = state.to_dict()
        assert d["last_event_id"] is None
        assert d["last_event_occurred_at"] is None
        assert d["created_at"] is None
        assert d["updated_at"] is None


# ---------------------------------------------------------------------------
# 8. from_dict deserialization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFromDict:
    """Tests for from_dict deserialization and backward compatibility."""

    def test_round_trip_empty_state(self) -> None:
        """to_dict -> from_dict preserves a minimal state."""
        original = CompositeCheckpointState(composite_name="c", run_id="r")
        restored = CompositeCheckpointState.from_dict(original.to_dict())

        assert restored.composite_name == "c"
        assert restored.run_id == "r"
        assert restored.state == CompositePipelineState.NOT_STARTED
        assert restored.seed_completed is False
        assert restored.seed_result is None

    def test_round_trip_full_state(self) -> None:
        """to_dict -> from_dict preserves all fields including results."""
        seed = _make_seed_result()
        dep = _make_dependency_result(pipeline_name="uniprot")
        er = _make_enrichment_result(enricher_name="crossref")
        created = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        updated = datetime(2024, 1, 2, 0, 0, tzinfo=UTC)

        original = CompositeCheckpointState(
            composite_name="my_comp",
            run_id="run-xyz",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            seed_result=seed,
            completed_dependencies=frozenset({"uniprot"}),
            dependency_results={"uniprot": dep},
            completed_enrichers=frozenset({"crossref"}),
            enrichment_results={"crossref": er},
            manifest_id="manifest-123",
            last_event_id="evt-123",
            last_event_occurred_at=updated,
            created_at=created,
            updated_at=updated,
        )
        restored = CompositeCheckpointState.from_dict(original.to_dict())

        assert restored.composite_name == "my_comp"
        assert restored.run_id == "run-xyz"
        assert restored.state == CompositePipelineState.ENRICHING
        assert restored.seed_completed is True
        assert restored.seed_result is not None
        assert restored.seed_result.pipeline_name == seed.pipeline_name
        assert restored.seed_result.records_extracted == seed.records_extracted
        assert "uniprot" in restored.completed_dependencies
        assert restored.dependency_results["uniprot"].pipeline_name == dep.pipeline_name
        assert "crossref" in restored.completed_enrichers
        assert restored.enrichment_results["crossref"].enricher_name == er.enricher_name
        assert restored.manifest_id == "manifest-123"
        assert restored.last_event_id == "evt-123"
        assert restored.last_event_occurred_at == updated
        assert restored.created_at == created
        assert restored.updated_at == updated

    def test_missing_optional_fields_use_defaults(self) -> None:
        """from_dict handles dicts missing optional fields (backward compat)."""
        minimal = {
            "composite_name": "c",
            "run_id": "r",
        }
        state = CompositeCheckpointState.from_dict(minimal)
        assert state.state == CompositePipelineState.NOT_STARTED
        assert state.seed_completed is False
        assert state.seed_result is None
        assert state.completed_dependencies == frozenset()
        assert state.completed_enrichers == frozenset()
        assert state.last_event_id is None
        assert state.last_event_occurred_at is None
        assert state.contract_version == ""

    def test_runtime_anchors_are_normalized_during_round_trip(self) -> None:
        """Checkpoint serialization/deserialization canonicalizes runtime anchors."""
        effective_config_hash = " SHA256:" + ("ABCDEF12" * 8) + " "
        original = CompositeCheckpointState(
            composite_name="c",
            run_id="r",
            effective_config_hash=effective_config_hash,
            contract_ref=" ChemBL.Activity ",
            contract_version=" v2 ",
            manifest_id=" manifest-123 ",
            composite_run_identity=" run-42 ",
        )

        payload = original.to_dict()
        restored = CompositeCheckpointState.from_dict(payload)

        assert payload["effective_config_hash"] == ("abcdef12" * 8)
        assert payload["contract_ref"] == "chembl.activity"
        assert payload["contract_version"] == "2.0.0"
        assert payload["manifest_id"] == "manifest-123"
        assert payload["composite_run_identity"] == "run-42"
        assert restored.effective_config_hash == ("abcdef12" * 8)
        assert restored.contract_ref == "chembl.activity"
        assert restored.contract_version == "2.0.0"
        assert restored.manifest_id == "manifest-123"
        assert restored.composite_run_identity == "run-42"

    def test_invalid_state_value_falls_back_to_not_started(self) -> None:
        """Corrupted state value produces NOT_STARTED without raising."""
        data = {
            "composite_name": "c",
            "run_id": "r",
            "state": "COMPLETELY_UNKNOWN",
        }
        state = CompositeCheckpointState.from_dict(data)
        assert state.state == CompositePipelineState.NOT_STARTED

    def test_empty_string_state_falls_back_to_not_started(self) -> None:
        """Empty string state value falls back to NOT_STARTED."""
        data = {"composite_name": "c", "run_id": "r", "state": ""}
        state = CompositeCheckpointState.from_dict(data)
        assert state.state == CompositePipelineState.NOT_STARTED

    def test_naive_created_at_gets_utc(self) -> None:
        """Naive ISO datetime strings gain UTC timezone info."""
        data = {
            "composite_name": "c",
            "run_id": "r",
            "created_at": "2024-06-15T08:00:00",  # no tzinfo
        }
        state = CompositeCheckpointState.from_dict(data)
        assert state.created_at is not None
        assert state.created_at.tzinfo is UTC

    def test_naive_updated_at_gets_utc(self) -> None:
        """Naive ISO datetime string for updated_at gains UTC timezone info."""
        data = {
            "composite_name": "c",
            "run_id": "r",
            "updated_at": "2024-06-15T09:00:00",
        }
        state = CompositeCheckpointState.from_dict(data)
        assert state.updated_at is not None
        assert state.updated_at.tzinfo is UTC

    def test_naive_last_event_occurred_at_gets_utc(self) -> None:
        """Naive ISO datetime string for watermark timestamp gains UTC timezone."""
        data = {
            "composite_name": "c",
            "run_id": "r",
            "last_event_id": "evt-123",
            "last_event_occurred_at": "2024-06-15T10:00:00",
        }
        state = CompositeCheckpointState.from_dict(data)
        assert state.last_event_id == "evt-123"
        assert state.last_event_occurred_at is not None
        assert state.last_event_occurred_at.tzinfo is UTC

    def test_dependency_status_deserialized(self) -> None:
        """Dependency status string is converted back to DependencyStatus enum."""
        data = {
            "composite_name": "c",
            "run_id": "r",
            "completed_dependencies": ["uniprot"],
            "dependency_results": {
                "uniprot": {
                    "pipeline_name": "uniprot",
                    "status": "failed",
                    "records_extracted": 0,
                    "records_silver": 0,
                    "duration_seconds": 1.0,
                    "error_message": "timeout",
                    "resumed": False,
                }
            },
        }
        state = CompositeCheckpointState.from_dict(data)
        assert state.dependency_results["uniprot"].status == DependencyStatus.FAILED

    def test_enrichment_status_deserialized(self) -> None:
        """Enrichment status string is converted back to EnrichmentStatus enum."""
        data = {
            "composite_name": "c",
            "run_id": "r",
            "completed_enrichers": ["crossref"],
            "enrichment_results": {
                "crossref": {
                    "enricher_name": "crossref",
                    "status": "partial",
                    "records_input": 100,
                    "records_enriched": 60,
                    "records_not_found": 40,
                    "records_errored": 0,
                    "dq_error_rate": 0.0,
                    "duration_seconds": 5.0,
                    "error_message": None,
                }
            },
        }
        state = CompositeCheckpointState.from_dict(data)
        assert state.enrichment_results["crossref"].status == EnrichmentStatus.PARTIAL


# ---------------------------------------------------------------------------
# 9. Immutability
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImmutability:
    """Tests that frozen dataclass semantics hold."""

    def test_direct_attribute_assignment_raises(self) -> None:
        """Frozen dataclass prevents direct attribute mutation."""
        state = CompositeCheckpointState(composite_name="c", run_id="r")
        with pytest.raises(AttributeError):
            state.state = CompositePipelineState.COMPLETED  # type: ignore[misc]

    def test_with_seed_completed_does_not_change_original(self) -> None:
        """Original state is unchanged after with_seed_completed."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        _ = initial.with_seed_completed(_make_seed_result())
        assert initial.seed_completed is False
        assert initial.state == CompositePipelineState.NOT_STARTED

    def test_with_enricher_completed_does_not_change_original(self) -> None:
        """Original state is unchanged after with_enricher_completed."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        _ = initial.with_enricher_completed("e1", _make_enrichment_result())
        assert initial.completed_enrichers == frozenset()

    def test_with_state_does_not_change_original(self) -> None:
        """Original state is unchanged after with_state."""
        initial = CompositeCheckpointState(composite_name="c", run_id="r")
        _ = initial.with_state(CompositePipelineState.FAILED)
        assert initial.state == CompositePipelineState.NOT_STARTED
