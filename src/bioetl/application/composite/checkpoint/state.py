"""Composite checkpoint state model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint import _state_support as state_support
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.normalization import normalize_runtime_anchor_payload
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.ports import ClockPort


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
    effective_config_artifact_id: str = ""
    execution_fingerprint: str = ""
    dq_contract_compatibility_hash: str = ""
    input_snapshot_fingerprint: str = ""
    contract_ref: str = ""
    contract_version: str = ""
    manifest_id: str = ""
    composite_run_identity: str = ""
    last_event_id: str | None = None
    last_event_occurred_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def with_seed_completed(
        self,
        result: SeedResult,
        *,
        clock: ClockPort | None = None,
    ) -> CompositeCheckpointState:
        """Return a copy with completed seed metadata."""
        return state_support.with_seed_completed(self, result, clock=clock)

    def with_dependency_completed(
        self,
        dependency_name: str,
        result: DependencyResult,
        *,
        clock: ClockPort | None = None,
    ) -> CompositeCheckpointState:
        """Return a copy with a completed dependency."""
        return state_support.with_dependency_completed(
            self,
            dependency_name,
            result,
            clock=clock,
        )

    def with_enricher_completed(
        self,
        enricher_name: str,
        result: EnrichmentResult,
        *,
        clock: ClockPort | None = None,
    ) -> CompositeCheckpointState:
        """Return a copy with a completed enricher."""
        return state_support.with_enricher_completed(
            self,
            enricher_name,
            result,
            clock=clock,
        )

    def with_state(
        self,
        new_state: CompositePipelineState,
        *,
        clock: ClockPort | None = None,
    ) -> CompositeCheckpointState:
        """Return a copy with an updated FSM state."""
        return state_support.with_state(self, new_state, clock=clock)

    def with_merge_completed(
        self,
        result: JsonDict,
        *,
        clock: ClockPort | None = None,
    ) -> CompositeCheckpointState:
        """Return a copy with completed merge metadata."""
        return state_support.with_merge_completed(self, result, clock=clock)

    @property
    def is_resumable(self) -> bool:
        """Check if this checkpoint can be resumed."""
        return state_support.is_resumable(self)

    def to_dict(self) -> dict[str, object]:
        """Convert state to JSON-compatible dictionary."""
        normalized_anchors = normalize_runtime_anchor_payload(
            {
                "effective_config_hash": self.effective_config_hash,
                "effective_config_artifact_id": self.effective_config_artifact_id,
                "execution_fingerprint": self.execution_fingerprint,
                "dq_contract_compatibility_hash": self.dq_contract_compatibility_hash,
                "input_snapshot_fingerprint": self.input_snapshot_fingerprint,
                "contract_ref": self.contract_ref,
                "contract_version": self.contract_version,
                "manifest_id": self.manifest_id,
                "composite_run_identity": self.composite_run_identity,
            }
        )
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
            "effective_config_hash": normalized_anchors["effective_config_hash"],
            "effective_config_artifact_id": normalized_anchors[
                "effective_config_artifact_id"
            ],
            "execution_fingerprint": normalized_anchors["execution_fingerprint"],
            "dq_contract_compatibility_hash": normalized_anchors[
                "dq_contract_compatibility_hash"
            ],
            "input_snapshot_fingerprint": normalized_anchors[
                "input_snapshot_fingerprint"
            ],
            "contract_ref": normalized_anchors["contract_ref"],
            "contract_version": normalized_anchors["contract_version"],
            "manifest_id": normalized_anchors["manifest_id"],
            "composite_run_identity": normalized_anchors["composite_run_identity"],
            "last_event_id": self.last_event_id,
            "last_event_occurred_at": (
                self.last_event_occurred_at.isoformat()
                if self.last_event_occurred_at
                else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(
        cls,
        data: JsonDict,  # Any: checkpoint state has heterogeneous values
    ) -> CompositeCheckpointState:
        """Rebuild state from serialized payload."""
        normalized_anchors = normalize_runtime_anchor_payload(
            {
                "effective_config_hash": data.get("effective_config_hash"),
                "effective_config_artifact_id": data.get(
                    "effective_config_artifact_id"
                ),
                "execution_fingerprint": data.get("execution_fingerprint"),
                "dq_contract_compatibility_hash": data.get(
                    "dq_contract_compatibility_hash"
                ),
                "input_snapshot_fingerprint": data.get("input_snapshot_fingerprint"),
                "contract_ref": data.get("contract_ref"),
                "contract_version": data.get("contract_version"),
                "manifest_id": data.get("manifest_id"),
                "composite_run_identity": data.get("composite_run_identity"),
            }
        )
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
            effective_config_hash=normalized_anchors["effective_config_hash"] or "",
            effective_config_artifact_id=(
                normalized_anchors["effective_config_artifact_id"] or ""
            ),
            execution_fingerprint=normalized_anchors["execution_fingerprint"] or "",
            dq_contract_compatibility_hash=(
                normalized_anchors["dq_contract_compatibility_hash"] or ""
            ),
            input_snapshot_fingerprint=(
                normalized_anchors["input_snapshot_fingerprint"] or ""
            ),
            contract_ref=normalized_anchors["contract_ref"] or "",
            contract_version=normalized_anchors["contract_version"] or "",
            manifest_id=normalized_anchors["manifest_id"] or "",
            composite_run_identity=normalized_anchors["composite_run_identity"] or "",
            last_event_id=_parse_optional_string(data.get("last_event_id")),
            last_event_occurred_at=_parse_timestamp(data.get("last_event_occurred_at")),
            created_at=_parse_timestamp(data.get("created_at")),
            updated_at=_parse_timestamp(data.get("updated_at")),
        )


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


def _parse_optional_string(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value


def _parse_state(value: object) -> CompositePipelineState:
    if not isinstance(value, str) or not value:
        return CompositePipelineState.NOT_STARTED
    try:
        return CompositePipelineState(value)
    except ValueError:
        return CompositePipelineState.NOT_STARTED
