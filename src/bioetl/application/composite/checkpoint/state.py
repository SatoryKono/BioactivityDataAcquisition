"""Composite checkpoint state model."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

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
    merge_completed: bool = False
    merge_result: JsonDict | None = None
    checkpoint_schema_version: str = "1.0.0"
    effective_config_hash: str = ""
    contract_ref: str = ""
    contract_version: str = "1.0.0"
    composite_run_identity: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def with_seed_completed(self, result: SeedResult) -> CompositeCheckpointState:
        """Return a copy with completed seed metadata."""
        return _replace_checkpoint_state(
            self,
            state=CompositePipelineState.SEED_COMPLETED,
            seed_completed=True,
            seed_result=result,
        )

    def with_dependency_completed(
        self,
        dependency_name: str,
        result: DependencyResult,
    ) -> CompositeCheckpointState:
        """Return a copy with a completed dependency."""
        return _replace_checkpoint_state(
            self,
            state=CompositePipelineState.DEPENDENCIES_RUNNING,
            completed_dependencies=frozenset(
                {*self.completed_dependencies, dependency_name}
            ),
            dependency_results={**self.dependency_results, dependency_name: result},
        )

    def with_enricher_completed(
        self,
        enricher_name: str,
        result: EnrichmentResult,
    ) -> CompositeCheckpointState:
        """Return a copy with a completed enricher."""
        return _replace_checkpoint_state(
            self,
            state=CompositePipelineState.ENRICHING,
            completed_enrichers=frozenset({*self.completed_enrichers, enricher_name}),
            enrichment_results={**self.enrichment_results, enricher_name: result},
        )

    def with_state(self, new_state: CompositePipelineState) -> CompositeCheckpointState:
        """Return a copy with an updated FSM state."""
        return _replace_checkpoint_state(self, state=new_state)

    def with_merge_completed(self, result: JsonDict) -> CompositeCheckpointState:
        """Return a copy with completed merge metadata."""
        return _replace_checkpoint_state(
            self,
            state=CompositePipelineState.MERGING,
            merge_completed=True,
            merge_result=result,
        )

    @property
    def is_resumable(self) -> bool:
        """Check if this checkpoint can be resumed."""
        return (
            self.state.is_resumable
            or self.seed_completed
            or bool(self.completed_enrichers)
        )

    def to_dict(self) -> dict[str, object]:
        """Convert state to JSON-compatible dictionary."""
        return {
            "composite_name": self.composite_name,
            "run_id": self.run_id,
            "state": self.state.value,
            "seed_completed": self.seed_completed,
            "seed_result": _serialize_seed_result(self.seed_result),
            "completed_dependencies": list(self.completed_dependencies),
            "dependency_results": _serialize_dependency_results(
                self.dependency_results
            ),
            "completed_enrichers": list(self.completed_enrichers),
            "enrichment_results": _serialize_enrichment_results(
                self.enrichment_results
            ),
            "merge_completed": self.merge_completed,
            "merge_result": self.merge_result,
            "checkpoint_schema_version": self.checkpoint_schema_version,
            "effective_config_hash": self.effective_config_hash,
            "contract_ref": self.contract_ref,
            "contract_version": self.contract_version,
            "composite_run_identity": self.composite_run_identity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(
        cls,
        data: JsonDict,  # Any: checkpoint state has heterogeneous values
    ) -> CompositeCheckpointState:
        """Rebuild state from serialized payload."""
        return cls(
            composite_name=data["composite_name"],
            run_id=data["run_id"],
            state=_parse_state(data.get("state")),
            seed_completed=data.get("seed_completed", False),
            seed_result=_parse_seed_result(data.get("seed_result")),
            completed_dependencies=frozenset(data.get("completed_dependencies", [])),
            dependency_results=_parse_dependency_results(
                data.get("dependency_results")
            ),
            completed_enrichers=frozenset(data.get("completed_enrichers", [])),
            enrichment_results=_parse_enrichment_results(
                data.get("enrichment_results")
            ),
            merge_completed=data.get("merge_completed", False),
            merge_result=data.get("merge_result"),
            checkpoint_schema_version=data.get("checkpoint_schema_version", "1.0.0"),
            effective_config_hash=data.get("effective_config_hash", ""),
            contract_ref=data.get("contract_ref", ""),
            contract_version=data.get("contract_version", "1.0.0"),
            composite_run_identity=data.get("composite_run_identity", ""),
            created_at=_parse_timestamp(data.get("created_at")),
            updated_at=_parse_timestamp(data.get("updated_at")),
        )


def _replace_checkpoint_state(
    checkpoint_state: CompositeCheckpointState,
    **changes: object,
) -> CompositeCheckpointState:
    # `dataclasses.replace` accepts field-aligned keyword overrides, but mypy
    # cannot infer them from a generic kwargs dict in this helper.
    typed_changes = dict[str, Any](changes)
    return replace(checkpoint_state, updated_at=datetime.now(tz=UTC), **typed_changes)


def _serialize_seed_result(result: SeedResult | None) -> dict[str, object] | None:
    if result is None:
        return None
    return {
        "pipeline_name": result.pipeline_name,
        "records_extracted": result.records_extracted,
        "records_silver": result.records_silver,
        "keys_generated": result.keys_generated,
        "duration_seconds": result.duration_seconds,
        "resumed": result.resumed,
    }


def _serialize_dependency_results(
    results: dict[str, DependencyResult],
) -> dict[str, dict[str, object]]:
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
        for name, result in results.items()
    }


def _serialize_enrichment_results(
    results: dict[str, EnrichmentResult],
) -> dict[str, dict[str, object]]:
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
        for name, result in results.items()
    }


def _parse_seed_result(value: object) -> SeedResult | None:
    if not isinstance(value, dict):
        return None
    return SeedResult(
        pipeline_name=value["pipeline_name"],
        records_extracted=value.get("records_extracted", 0),
        records_silver=value.get("records_silver", 0),
        keys_generated=value.get("keys_generated", 0),
        duration_seconds=value.get("duration_seconds", 0.0),
        resumed=value.get("resumed", False),
    )


def _parse_dependency_results(value: object) -> dict[str, DependencyResult]:
    if not isinstance(value, dict):
        return {}
    return {
        name: _parse_dependency_result(payload)
        for name, payload in value.items()
        if isinstance(name, str) and isinstance(payload, dict)
    }


def _parse_dependency_result(payload: JsonDict) -> DependencyResult:
    return DependencyResult(
        pipeline_name=payload["pipeline_name"],
        status=DependencyStatus(payload["status"]),
        records_extracted=payload.get("records_extracted", 0),
        records_silver=payload.get("records_silver", 0),
        duration_seconds=payload.get("duration_seconds", 0.0),
        error_message=payload.get("error_message"),
        resumed=payload.get("resumed", False),
    )


def _parse_enrichment_results(value: object) -> dict[str, EnrichmentResult]:
    if not isinstance(value, dict):
        return {}
    return {
        name: _parse_enrichment_result(payload)
        for name, payload in value.items()
        if isinstance(name, str) and isinstance(payload, dict)
    }


def _parse_enrichment_result(payload: JsonDict) -> EnrichmentResult:
    return EnrichmentResult(
        enricher_name=payload["enricher_name"],
        status=EnrichmentStatus(payload["status"]),
        records_input=payload.get("records_input", 0),
        records_enriched=payload.get("records_enriched", 0),
        records_not_found=payload.get("records_not_found", 0),
        records_errored=payload.get("records_errored", 0),
        dq_error_rate=payload.get("dq_error_rate", 0.0),
        duration_seconds=payload.get("duration_seconds", 0.0),
        error_message=payload.get("error_message"),
    )


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _parse_state(value: object) -> CompositePipelineState:
    if not isinstance(value, str) or not value:
        return CompositePipelineState.NOT_STARTED
    try:
        return CompositePipelineState(value)
    except ValueError:
        return CompositePipelineState.NOT_STARTED
