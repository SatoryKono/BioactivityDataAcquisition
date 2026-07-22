"""Composite checkpoint state serialization helpers."""

from __future__ import annotations

from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    SeedResult,
)


def serialize_seed_result(result: SeedResult | None) -> dict[str, object] | None:
    """Serialize a seed result into checkpoint payload form."""
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


def serialize_dependency_results(
    results: dict[str, DependencyResult],
) -> dict[str, dict[str, object]]:
    """Serialize dependency results into checkpoint payload form."""
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
        for name, result in sorted(results.items())
    }


def serialize_enrichment_results(
    results: dict[str, EnrichmentResult],
) -> dict[str, dict[str, object]]:
    """Serialize enrichment results into checkpoint payload form."""
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
        for name, result in sorted(results.items())
    }


__all__ = [
    "serialize_dependency_results",
    "serialize_enrichment_results",
    "serialize_seed_result",
]
