"""Pure helper functions for mergeable runner inputs."""

from __future__ import annotations

from collections.abc import Iterable, Set

from bioetl.domain.composite.config import DependencyConfig, EnricherConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
)
from bioetl.domain.ports import LoggerPort

_DEPENDENCY_EXCLUDED_LOG = "Excluding dependency from merge"


def add_not_run_results(
    enrichment_results: dict[str, EnrichmentResult],
    enrichers_to_run: list[EnricherConfig],
    all_enrichers: Iterable[EnricherConfig],
    completed_enrichers: Set[str],
    required_only: bool,
    composite_name: str,
    logger: LoggerPort,
) -> dict[str, EnrichmentResult]:
    """Mark optional enrichers skipped in required-only mode as NOT_RUN."""
    if not required_only:
        return enrichment_results
    run_names = {enricher.pipeline for enricher in enrichers_to_run}
    for enricher in all_enrichers:
        if enricher.required:
            continue
        if enricher.pipeline in run_names:
            continue
        if enricher.pipeline in completed_enrichers:
            continue
        if enricher.pipeline in enrichment_results:
            continue
        enrichment_results[enricher.pipeline] = EnrichmentResult.not_run(
            enricher_name=enricher.pipeline,
            reason="Skipped due to required_only mode",
        )
        logger.info(
            "Optional enricher not run",
            composite=composite_name,
            enricher=enricher.pipeline,
            reason="required_only_mode",
        )
    return enrichment_results


def get_mergeable_enrichers(
    enrichment_results: dict[str, EnrichmentResult],
    all_enrichers: Iterable[EnricherConfig],
    logger: LoggerPort,
) -> list[EnricherConfig]:
    """Get enrichers that have mergeable data available."""
    non_mergeable_statuses = (
        EnrichmentStatus.SKIPPED,
        EnrichmentStatus.NOT_RUN,
    )
    mergeable: list[EnricherConfig] = []
    for enricher_cfg in all_enrichers:
        result = enrichment_results.get(enricher_cfg.pipeline)
        if result is None:
            continue
        if result.status in non_mergeable_statuses:
            logger.debug(
                "Excluding enricher from merge",
                enricher=enricher_cfg.pipeline,
                status=result.status.value,
                reason="no_data_to_merge",
            )
            continue
        mergeable.append(enricher_cfg)
    return mergeable


def get_mergeable_dependencies(
    dependency_results: dict[str, DependencyResult],
    all_dependencies: Iterable[DependencyConfig],
    logger: LoggerPort,
) -> list[DependencyConfig]:
    """Get dependencies that have mergeable data available."""
    mergeable: list[DependencyConfig] = []
    for dependency_cfg in all_dependencies:
        result = dependency_results.get(dependency_cfg.pipeline)
        if result is None:
            logger.debug(
                _DEPENDENCY_EXCLUDED_LOG,
                dependency=dependency_cfg.pipeline,
                reason="no_result",
            )
            continue
        if not dependency_cfg.silver_table:
            logger.debug(
                _DEPENDENCY_EXCLUDED_LOG,
                dependency=dependency_cfg.pipeline,
                reason="no_silver_table",
            )
            continue
        if result.is_success or result.status == DependencyStatus.SKIPPED:
            mergeable.append(dependency_cfg)
            continue
        logger.debug(
            _DEPENDENCY_EXCLUDED_LOG,
            dependency=dependency_cfg.pipeline,
            status=result.status.value,
            reason="execution_failed_or_timed_out",
        )
    return mergeable


__all__ = [
    "add_not_run_results",
    "get_mergeable_dependencies",
    "get_mergeable_enrichers",
]
