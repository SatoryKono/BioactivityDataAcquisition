"""Composite checkpoint state model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

import bioetl.application.composite.checkpoint._state_support as state_support
from bioetl.application.composite.checkpoint.state_parsing import (
    parse_dependency_results,
    parse_enrichment_results,
    parse_optional_string,
    parse_seed_result,
    parse_state,
    parse_timestamp,
)
from bioetl.application.composite.checkpoint.state_serialization import (
    serialize_dependency_results,
    serialize_enrichment_results,
    serialize_seed_result,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
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
            "seed_result": serialize_seed_result(self.seed_result),
            "completed_dependencies": list(self.completed_dependencies),
            "dependency_results": serialize_dependency_results(
                self.dependency_results
            ),
            "completed_enrichers": list(self.completed_enrichers),
            "enrichment_results": serialize_enrichment_results(
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
            state=parse_state(data.get("state")),
            seed_completed=data.get("seed_completed", False),
            seed_result=parse_seed_result(data.get("seed_result")),
            completed_dependencies=frozenset(data.get("completed_dependencies", [])),
            dependency_results=parse_dependency_results(
                data.get("dependency_results")
            ),
            completed_enrichers=frozenset(data.get("completed_enrichers", [])),
            enrichment_results=parse_enrichment_results(
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
            last_event_id=parse_optional_string(data.get("last_event_id")),
            last_event_occurred_at=parse_timestamp(data.get("last_event_occurred_at")),
            created_at=parse_timestamp(data.get("created_at")),
            updated_at=parse_timestamp(data.get("updated_at")),
        )
