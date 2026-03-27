"""Serialization helpers for composite checkpoint state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint.state import CompositeCheckpointState


def to_dict(checkpoint_state: CompositeCheckpointState) -> dict[str, object]:
    """Convert checkpoint state to a JSON-compatible dictionary."""
    return {
        "composite_name": checkpoint_state.composite_name,
        "run_id": checkpoint_state.run_id,
        "state": checkpoint_state.state.value,
        "seed_completed": checkpoint_state.seed_completed,
        "seed_result": _serialize_seed_result(checkpoint_state.seed_result),
        "completed_dependencies": list(checkpoint_state.completed_dependencies),
        "dependency_results": _serialize_dependency_results(
            checkpoint_state.dependency_results
        ),
        "completed_enrichers": list(checkpoint_state.completed_enrichers),
        "enrichment_results": _serialize_enrichment_results(
            checkpoint_state.enrichment_results
        ),
        "merge_completed": checkpoint_state.merge_completed,
        "merge_result": checkpoint_state.merge_result,
        "checkpoint_schema_version": checkpoint_state.checkpoint_schema_version,
        "effective_config_hash": checkpoint_state.effective_config_hash,
        "contract_ref": checkpoint_state.contract_ref,
        "contract_version": checkpoint_state.contract_version,
        "composite_run_identity": checkpoint_state.composite_run_identity,
        "created_at": (
            checkpoint_state.created_at.isoformat()
            if checkpoint_state.created_at
            else None
        ),
        "updated_at": (
            checkpoint_state.updated_at.isoformat()
            if checkpoint_state.updated_at
            else None
        ),
    }


def from_dict(data: JsonDict) -> CompositeCheckpointState:
    """Rebuild checkpoint state from serialized payload."""
    from bioetl.application.composite.checkpoint.state import CompositeCheckpointState

    return CompositeCheckpointState(
        composite_name=data["composite_name"],
        run_id=data["run_id"],
        state=_parse_state(data.get("state")),
        seed_completed=data.get("seed_completed", False),
        seed_result=_parse_seed_result(data.get("seed_result")),
        completed_dependencies=frozenset(data.get("completed_dependencies", [])),
        dependency_results=_parse_dependency_results(data.get("dependency_results")),
        completed_enrichers=frozenset(data.get("completed_enrichers", [])),
        enrichment_results=_parse_enrichment_results(data.get("enrichment_results")),
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
