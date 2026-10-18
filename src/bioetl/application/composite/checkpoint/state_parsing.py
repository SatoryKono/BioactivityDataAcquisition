"""Composite checkpoint state parsing helpers."""

from __future__ import annotations

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


def parse_seed_result(value: object) -> SeedResult | None:
    """Parse a seed result from checkpoint payload form."""
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


def parse_dependency_results(value: object) -> dict[str, DependencyResult]:
    """Parse dependency results from checkpoint payload form."""
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


def parse_enrichment_results(value: object) -> dict[str, EnrichmentResult]:
    """Parse enrichment results from checkpoint payload form."""
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


def parse_timestamp(value: object) -> datetime | None:
    """Parse a timestamp from checkpoint payload form."""
    if not isinstance(value, str) or not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def parse_optional_string(value: object) -> str | None:
    """Parse a non-empty optional string."""
    if not isinstance(value, str) or not value:
        return None
    return value


def parse_state(value: object) -> CompositePipelineState:
    """Parse a composite state with fail-closed fallback."""
    if not isinstance(value, str) or not value:
        return CompositePipelineState.NOT_STARTED
    try:
        return CompositePipelineState(value)
    except ValueError:
        return CompositePipelineState.NOT_STARTED


__all__ = [
    "parse_dependency_results",
    "parse_enrichment_results",
    "parse_optional_string",
    "parse_seed_result",
    "parse_state",
    "parse_timestamp",
]
