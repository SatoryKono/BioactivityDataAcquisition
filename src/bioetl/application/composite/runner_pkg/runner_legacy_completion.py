"""Finalization-only resume for completed legacy CV checkpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.runtime_models import CompositeExecutionContext
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.exceptions import CheckpointConflictError

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint import CompositeCheckpointState


def legacy_completed_execution_context(
    state: CompositeCheckpointState,
) -> CompositeExecutionContext:
    """Build terminal context from persisted evidence without rerunning merge."""
    if not state.seed_completed or state.seed_result is None:
        raise CheckpointConflictError(
            state.composite_name,
            "legacy cross_validation_completed checkpoint lacks completed seed result",
        )
    payload = state.merge_result
    if not isinstance(payload, dict) or not isinstance(
        payload.get("records_merged"), int
    ):
        raise CheckpointConflictError(
            state.composite_name,
            "legacy cross_validation_completed checkpoint lacks merge result evidence",
        )

    merge_fields = {
        "records_merged",
        "records_from_seed",
        "records_enriched",
        "records_fully_enriched",
        "sources_used",
        "field_coverage",
        "duration_seconds",
        "output_silver_path",
        "output_gold_path",
        "lineage_summary",
        "quarantine_payloads",
    }
    merge_result = MergeResult(
        **{key: value for key, value in payload.items() if key in merge_fields}
    )
    return CompositeExecutionContext(
        seed_result=state.seed_result,
        dependency_results=state.dependency_results,
        enrichment_results=state.enrichment_results,
        merge_result=merge_result,
    )
