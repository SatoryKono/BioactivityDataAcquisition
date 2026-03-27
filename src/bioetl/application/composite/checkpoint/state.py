"""Composite checkpoint state model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from bioetl.application.composite.checkpoint import _state_codec as state_codec
from bioetl.application.composite.checkpoint import _state_support as state_support
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
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
        return state_support.with_seed_completed(self, result)

    def with_dependency_completed(
        self,
        dependency_name: str,
        result: DependencyResult,
    ) -> CompositeCheckpointState:
        """Return a copy with a completed dependency."""
        return state_support.with_dependency_completed(self, dependency_name, result)

    def with_enricher_completed(
        self,
        enricher_name: str,
        result: EnrichmentResult,
    ) -> CompositeCheckpointState:
        """Return a copy with a completed enricher."""
        return state_support.with_enricher_completed(self, enricher_name, result)

    def with_state(self, new_state: CompositePipelineState) -> CompositeCheckpointState:
        """Return a copy with an updated FSM state."""
        return state_support.with_state(self, new_state)

    def with_merge_completed(self, result: JsonDict) -> CompositeCheckpointState:
        """Return a copy with completed merge metadata."""
        return state_support.with_merge_completed(self, result)

    @property
    def is_resumable(self) -> bool:
        """Check if this checkpoint can be resumed."""
        return state_support.is_resumable(self)

    def to_dict(self) -> dict[str, object]:
        """Convert state to JSON-compatible dictionary."""
        return state_codec.to_dict(self)

    @classmethod
    def from_dict(
        cls,
        data: JsonDict,  # Any: checkpoint state has heterogeneous values
    ) -> CompositeCheckpointState:
        """Rebuild state from serialized payload."""
        return state_codec.from_dict(data)
