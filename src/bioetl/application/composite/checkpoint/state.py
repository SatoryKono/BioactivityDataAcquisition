"""Composite checkpoint state model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.types import JsonDict


@dataclass(frozen=True, slots=True)
class CompositeCheckpointState:
    """Immutable checkpoint state for composite pipeline."""

    composite_name: str
    run_id: str
    state: CompositePipelineState = CompositePipelineState.NOT_STARTED
    seed_completed: bool = False
    seed_result: SeedResult | None = None
    completed_dependencies: frozenset[str] = field(default_factory=frozenset)
    dependency_results: dict[str, DependencyResult] = field(default_factory=dict)
    completed_enrichers: frozenset[str] = field(default_factory=frozenset)
    enrichment_results: dict[str, EnrichmentResult] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def with_seed_completed(self, result: SeedResult) -> CompositeCheckpointState:
        """Create new state with seed marked as completed."""
        return CompositeCheckpointState(
            composite_name=self.composite_name,
            run_id=self.run_id,
            state=CompositePipelineState.SEED_COMPLETED,
            seed_completed=True,
            seed_result=result,
            completed_dependencies=self.completed_dependencies,
            dependency_results=self.dependency_results,
            completed_enrichers=self.completed_enrichers,
            enrichment_results=self.enrichment_results,
            created_at=self.created_at,
            updated_at=datetime.now(tz=UTC),
        )

    def with_dependency_completed(
        self,
        dependency_name: str,
        result: DependencyResult,
    ) -> CompositeCheckpointState:
        """Create new state with dependency marked as completed."""
        new_completed = self.completed_dependencies | {dependency_name}
        new_results = {**self.dependency_results, dependency_name: result}
        return CompositeCheckpointState(
            composite_name=self.composite_name,
            run_id=self.run_id,
            state=CompositePipelineState.DEPENDENCIES_RUNNING,
            seed_completed=self.seed_completed,
            seed_result=self.seed_result,
            completed_dependencies=frozenset(new_completed),
            dependency_results=new_results,
            completed_enrichers=self.completed_enrichers,
            enrichment_results=self.enrichment_results,
            created_at=self.created_at,
            updated_at=datetime.now(tz=UTC),
        )

    def with_enricher_completed(
        self,
        enricher_name: str,
        result: EnrichmentResult,
    ) -> CompositeCheckpointState:
        """Create new state with enricher marked as completed."""
        new_completed = self.completed_enrichers | {enricher_name}
        new_results = {**self.enrichment_results, enricher_name: result}
        return CompositeCheckpointState(
            composite_name=self.composite_name,
            run_id=self.run_id,
            state=CompositePipelineState.ENRICHING,
            seed_completed=self.seed_completed,
            seed_result=self.seed_result,
            completed_dependencies=self.completed_dependencies,
            dependency_results=self.dependency_results,
            completed_enrichers=frozenset(new_completed),
            enrichment_results=new_results,
            created_at=self.created_at,
            updated_at=datetime.now(tz=UTC),
        )

    def with_state(self, new_state: CompositePipelineState) -> CompositeCheckpointState:
        """Create new state with updated FSM state."""
        return CompositeCheckpointState(
            composite_name=self.composite_name,
            run_id=self.run_id,
            state=new_state,
            seed_completed=self.seed_completed,
            seed_result=self.seed_result,
            completed_dependencies=self.completed_dependencies,
            dependency_results=self.dependency_results,
            completed_enrichers=self.completed_enrichers,
            enrichment_results=self.enrichment_results,
            created_at=self.created_at,
            updated_at=datetime.now(tz=UTC),
        )

    @property
    def is_resumable(self) -> bool:
        """Check if this checkpoint can be resumed."""
        if self.state.is_resumable:
            return True
        return self.seed_completed or bool(self.completed_enrichers)

    def to_dict(self) -> dict[str, object]:
        """Convert state to dictionary for JSON serialization."""
        return {
            "composite_name": self.composite_name,
            "run_id": self.run_id,
            "state": self.state.value,
            "seed_completed": self.seed_completed,
            "seed_result": self._serialize_seed_result(),
            "completed_dependencies": list(self.completed_dependencies),
            "dependency_results": self._serialize_dependency_results(),
            "completed_enrichers": list(self.completed_enrichers),
            "enrichment_results": self._serialize_enrichment_results(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def _serialize_seed_result(self) -> dict[str, object] | None:
        if not self.seed_result:
            return None
        return {
            "pipeline_name": self.seed_result.pipeline_name,
            "records_extracted": self.seed_result.records_extracted,
            "records_silver": self.seed_result.records_silver,
            "keys_generated": self.seed_result.keys_generated,
            "duration_seconds": self.seed_result.duration_seconds,
            "resumed": self.seed_result.resumed,
        }

    def _serialize_dependency_results(self) -> dict[str, dict[str, object]]:
        return {
            name: {
                "pipeline_name": result.pipeline_name,
                "status": result.status.value,
                "records_extracted": result.records_extracted,
                "records_silver": result.records_silver,
                "duration_seconds": result.duration_seconds,
                "error_message": result.error_message,
                "resumed": result.resumed,
            }
            for name, result in self.dependency_results.items()
        }

    def _serialize_enrichment_results(self) -> dict[str, dict[str, object]]:
        return {
            name: {
                "enricher_name": result.enricher_name,
                "status": result.status.value,
                "records_input": result.records_input,
                "records_enriched": result.records_enriched,
                "records_not_found": result.records_not_found,
                "records_errored": result.records_errored,
                "dq_error_rate": result.dq_error_rate,
                "duration_seconds": result.duration_seconds,
                "error_message": result.error_message,
            }
            for name, result in self.enrichment_results.items()
        }

    @classmethod
    def from_dict(
        cls,
        data: JsonDict,  # Any: checkpoint state has heterogeneous values
    ) -> CompositeCheckpointState:
        """Create state from dictionary with backward-compatibility handling."""
        seed_result = None
        if data.get("seed_result"):
            sr = data["seed_result"]
            seed_result = SeedResult(
                pipeline_name=sr["pipeline_name"],
                records_extracted=sr.get("records_extracted", 0),
                records_silver=sr.get("records_silver", 0),
                keys_generated=sr.get("keys_generated", 0),
                duration_seconds=sr.get("duration_seconds", 0.0),
                resumed=sr.get("resumed", False),
            )

        dependency_results: dict[str, DependencyResult] = {}
        for name, dr_data in data.get("dependency_results", {}).items():
            dependency_results[name] = DependencyResult(
                pipeline_name=dr_data["pipeline_name"],
                status=DependencyStatus(dr_data["status"]),
                records_extracted=dr_data.get("records_extracted", 0),
                records_silver=dr_data.get("records_silver", 0),
                duration_seconds=dr_data.get("duration_seconds", 0.0),
                error_message=dr_data.get("error_message"),
                resumed=dr_data.get("resumed", False),
            )

        enrichment_results: dict[str, EnrichmentResult] = {}
        for name, er_data in data.get("enrichment_results", {}).items():
            enrichment_results[name] = EnrichmentResult(
                enricher_name=er_data["enricher_name"],
                status=EnrichmentStatus(er_data["status"]),
                records_input=er_data.get("records_input", 0),
                records_enriched=er_data.get("records_enriched", 0),
                records_not_found=er_data.get("records_not_found", 0),
                records_errored=er_data.get("records_errored", 0),
                dq_error_rate=er_data.get("dq_error_rate", 0.0),
                duration_seconds=er_data.get("duration_seconds", 0.0),
                error_message=er_data.get("error_message"),
            )

        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)

        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)

        state = CompositePipelineState.NOT_STARTED
        state_value = data.get("state")
        if state_value is not None:
            try:
                state = CompositePipelineState(state_value)
            except ValueError:
                state = CompositePipelineState.NOT_STARTED

        return cls(
            composite_name=data["composite_name"],
            run_id=data["run_id"],
            state=state,
            seed_completed=data.get("seed_completed", False),
            seed_result=seed_result,
            completed_dependencies=frozenset(data.get("completed_dependencies", [])),
            dependency_results=dependency_results,
            completed_enrichers=frozenset(data.get("completed_enrichers", [])),
            enrichment_results=enrichment_results,
            created_at=created_at,
            updated_at=updated_at,
        )
