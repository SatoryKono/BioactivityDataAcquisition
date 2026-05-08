"""Stable payload builders for composite runner stage orchestration."""

from __future__ import annotations

from collections.abc import Sequence

from bioetl.application.composite.runtime_models import (
    CompositeExecutionContext,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)

__all__ = [
    "build_composite_run_completion_metrics",
    "build_dependency_result_payload",
    "build_dependency_stage_details",
    "build_dependency_stage_metrics",
    "build_enrichment_result_payload",
    "build_enrichment_stage_details",
    "build_enrichment_stage_metrics",
    "build_merge_result_payload",
    "build_merge_stage_metrics",
    "build_seed_stage_metrics",
]


def _build_named_stage_details(
    *,
    field_name: str,
    names: Sequence[str],
) -> dict[str, object]:
    """Return a stable list-plus-count payload for one named stage collection."""
    normalized_names = [str(name) for name in names]
    return {
        field_name: normalized_names,
        "count": len(normalized_names),
    }


def build_dependency_stage_details(
    dependency_pipeline_names: Sequence[str],
) -> dict[str, object]:
    """Build stable dependency-stage details for logs and ledger payloads."""
    return _build_named_stage_details(
        field_name="dependencies",
        names=dependency_pipeline_names,
    )


def build_enrichment_stage_details(
    enricher_names: Sequence[str],
) -> dict[str, object]:
    """Build stable enrichment-stage details for logs and ledger payloads."""
    return _build_named_stage_details(
        field_name="enrichers",
        names=enricher_names,
    )


def build_seed_stage_metrics(seed_result: SeedResult) -> dict[str, int]:
    """Build stable seed-stage metrics for run-ledger payloads."""
    return {
        "records_extracted": int(seed_result.records_extracted),
        "records_silver": int(seed_result.records_silver),
        "keys_generated": int(seed_result.keys_generated),
    }


def build_dependency_stage_metrics(
    dependency_results: dict[str, DependencyResult],
) -> dict[str, int]:
    """Build dependency-stage metrics for run-ledger payloads."""
    succeeded = sum(1 for result in dependency_results.values() if result.is_success)
    return {
        "dependencies_total": len(dependency_results),
        "dependencies_succeeded": succeeded,
        "dependencies_failed": len(dependency_results) - succeeded,
    }


def build_dependency_result_payload(result: DependencyResult) -> dict[str, object]:
    """Build bounded dependency result evidence for run-ledger replay."""
    return {
        "pipeline_name": result.pipeline_name,
        "status": result.status.value,
        "records_extracted": int(result.records_extracted),
        "records_silver": int(result.records_silver),
        "duration_seconds": float(result.duration_seconds),
        "error_message": result.error_message,
        "resumed": bool(result.resumed),
    }


def build_enrichment_stage_metrics(
    enrichment_results: dict[str, EnrichmentResult],
) -> dict[str, int]:
    """Build enrichment-stage metrics for run-ledger payloads."""
    return {
        "enrichers_total": len(enrichment_results),
        "enrichers_succeeded": sum(
            1
            for result in enrichment_results.values()
            if result.status == EnrichmentStatus.SUCCESS
        ),
        "enrichers_failed": sum(
            1
            for result in enrichment_results.values()
            if result.status == EnrichmentStatus.FAILED
        ),
        "enrichers_skipped": sum(
            1
            for result in enrichment_results.values()
            if result.status == EnrichmentStatus.SKIPPED
        ),
    }


def build_enrichment_result_payload(result: EnrichmentResult) -> dict[str, object]:
    """Build bounded enricher result evidence for run-ledger replay."""
    return {
        "enricher_name": result.enricher_name,
        "status": result.status.value,
        "records_input": int(result.records_input),
        "records_enriched": int(result.records_enriched),
        "records_not_found": int(result.records_not_found),
        "records_errored": int(result.records_errored),
        "dq_error_rate": float(result.dq_error_rate),
        "duration_seconds": float(result.duration_seconds),
        "error_message": result.error_message,
    }


def build_merge_stage_metrics(merge_result: MergeResult) -> dict[str, int]:
    """Build merge-stage metrics for run-ledger payloads."""
    return {
        "records_merged": int(merge_result.records_merged),
        "records_from_seed": int(merge_result.records_from_seed),
        "records_enriched": int(merge_result.records_enriched),
        "records_fully_enriched": int(merge_result.records_fully_enriched),
    }


def build_merge_result_payload(merge_result: MergeResult) -> dict[str, object]:
    """Build bounded merge result evidence for run-ledger replay."""
    return {
        "records_merged": int(merge_result.records_merged),
        "records_from_seed": int(merge_result.records_from_seed),
        "records_enriched": int(merge_result.records_enriched),
        "records_fully_enriched": int(merge_result.records_fully_enriched),
        "sources_used": list(merge_result.sources_used),
        "field_coverage": dict(sorted(merge_result.field_coverage.items())),
        "duration_seconds": float(merge_result.duration_seconds),
        "output_silver_path": merge_result.output_silver_path,
        "output_gold_path": merge_result.output_gold_path,
        "lineage_summary": dict(sorted(merge_result.lineage_summary.items())),
        "quarantine_count": len(merge_result.quarantine_payloads),
    }


def build_composite_run_completion_metrics(
    artifacts: CompositeExecutionContext,
) -> dict[str, int]:
    """Build final aggregate metrics for composite run completion entries."""
    metrics = build_seed_stage_metrics(artifacts.seed_result)
    metrics.update(build_dependency_stage_metrics(artifacts.dependency_results))
    metrics.update(build_enrichment_stage_metrics(artifacts.enrichment_results))
    if artifacts.merge_result is not None:
        metrics.update(build_merge_stage_metrics(artifacts.merge_result))
    return metrics
