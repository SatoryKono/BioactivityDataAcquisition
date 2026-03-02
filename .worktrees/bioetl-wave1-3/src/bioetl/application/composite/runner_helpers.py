"""Helper functions for CompositePipelineRunner.

Pure functions extracted to reduce class size while maintaining cohesion.
These functions have no side effects and operate on data passed as arguments.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
)

if TYPE_CHECKING:
    from collections.abc import Set

    from bioetl.domain.composite.config import DependencyConfig, EnricherConfig
    from bioetl.domain.ports import LoggerPort


def log_enrichment_summary(
    enrichment_results: dict[str, EnrichmentResult],
    composite_name: str,
    logger: LoggerPort,
) -> None:
    """Log aggregated summary of enrichment results.

    Args:
        enrichment_results: Results from enrichers.
        composite_name: Name of the composite pipeline.
        logger: Logger port for structured logging.
    """
    if not enrichment_results:
        return

    # Aggregate by status using counter
    status_counts: dict[EnrichmentStatus, int] = dict.fromkeys(EnrichmentStatus, 0)
    total_records_input = 0
    total_records_enriched = 0
    total_records_errored = 0

    failed_enrichers: list[str] = []
    successful_enrichers: list[str] = []
    not_run_enrichers: list[str] = []

    # Track which statuses map to which enricher lists
    success_statuses = {EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL}
    failure_statuses = {EnrichmentStatus.FAILED, EnrichmentStatus.TIMEOUT}

    for name, result in enrichment_results.items():
        total_records_input += result.records_input
        total_records_enriched += result.records_enriched
        total_records_errored += result.records_errored
        status_counts[result.status] += 1

        # Categorize enrichers
        if result.status in success_statuses:
            successful_enrichers.append(name)
        elif result.status in failure_statuses:
            failed_enrichers.append(name)
        elif result.status == EnrichmentStatus.NOT_RUN:
            not_run_enrichers.append(name)

    logger.info(
        "Enrichment summary",
        composite=composite_name,
        total_enrichers=len(enrichment_results),
        success=status_counts[EnrichmentStatus.SUCCESS],
        partial=status_counts[EnrichmentStatus.PARTIAL],
        failed=status_counts[EnrichmentStatus.FAILED],
        skipped=status_counts[EnrichmentStatus.SKIPPED],
        timeout=status_counts[EnrichmentStatus.TIMEOUT],
        not_run=status_counts[EnrichmentStatus.NOT_RUN],
        successful_enrichers=successful_enrichers,
        failed_enrichers=failed_enrichers if failed_enrichers else None,
        not_run_enrichers=not_run_enrichers if not_run_enrichers else None,
        total_records_input=total_records_input,
        total_records_enriched=total_records_enriched,
        total_records_errored=total_records_errored,
    )


def calculate_had_warnings(
    enrichment_results: dict[str, EnrichmentResult],
    required_enrichers: frozenset[str],
    composite_name: str,
    logger: LoggerPort,
) -> bool:
    """Calculate if the pipeline had warnings from optional enricher failures.

    A warning occurs when an optional (non-required) enricher fails but the
    pipeline can still complete successfully. This allows users to distinguish
    between clean completions and completions with issues.

    Args:
        enrichment_results: All enrichment results.
        required_enrichers: Set of required enricher names.
        composite_name: Name of the composite pipeline.
        logger: Logger port for structured logging.

    Returns:
        True if any optional enricher failed (status FAILED or TIMEOUT).
    """
    for name, result in enrichment_results.items():
        # Skip required enrichers - their failures would already have raised
        if name in required_enrichers:
            continue

        # Check for failure statuses (FAILED, TIMEOUT)
        if result.status in (EnrichmentStatus.FAILED, EnrichmentStatus.TIMEOUT):
            logger.warning(
                "Optional enricher failed",
                composite=composite_name,
                enricher=name,
                status=result.status.value,
                error_message=result.error_message,
            )
            return True

    return False


def add_not_run_results(
    enrichment_results: dict[str, EnrichmentResult],
    enrichers_to_run: list[EnricherConfig],
    all_enrichers: Iterable[EnricherConfig],
    completed_enrichers: Set[str],
    required_only: bool,
    composite_name: str,
    logger: LoggerPort,
) -> dict[str, EnrichmentResult]:
    """Add NOT_RUN results for optional enrichers skipped due to required_only mode.

    When required_only is True, optional enrichers are not executed. This function
    adds explicit NOT_RUN results for these enrichers so they appear in the
    final enrichment_results for complete lineage tracking.

    Args:
        enrichment_results: Current enrichment results from executed enrichers.
        enrichers_to_run: List of enrichers that were actually run.
        all_enrichers: All enrichers in the config.
        completed_enrichers: Set of previously completed enricher names.
        required_only: Whether required_only mode is active.
        composite_name: Name of the composite pipeline.
        logger: Logger port for structured logging.

    Returns:
        Updated enrichment_results with NOT_RUN entries for skipped optional enrichers.
    """
    if not required_only:
        return enrichment_results

    # Get set of enrichers that were actually run or previously completed
    run_names = {e.pipeline for e in enrichers_to_run}

    # Find optional enrichers that were skipped due to required_only
    for enricher in all_enrichers:
        # Only process optional enrichers
        if enricher.required:
            continue

        # Skip if this enricher was run or previously completed
        if enricher.pipeline in run_names:
            continue
        if enricher.pipeline in completed_enrichers:
            continue

        # Skip if already in results (shouldn't happen, but defensive)
        if enricher.pipeline in enrichment_results:
            continue

        # Add NOT_RUN result for this skipped optional enricher
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
    """Get list of enrichers that should be included in merge.

    Excludes enrichers with NOT_RUN or SKIPPED status since they have no
    data to merge. This prevents file I/O errors when trying to read
    non-existent or empty Silver tables.

    Args:
        enrichment_results: All enrichment results.
        all_enrichers: All enricher configs.
        logger: Logger port for structured logging.

    Returns:
        List of EnricherConfig for enrichers that have data to merge.
    """
    # Statuses that indicate no data to merge
    non_mergeable_statuses = (
        EnrichmentStatus.SKIPPED,
        EnrichmentStatus.NOT_RUN,
    )

    mergeable: list[EnricherConfig] = []
    for enricher_cfg in all_enrichers:
        result = enrichment_results.get(enricher_cfg.pipeline)

        # If no result, don't include in merge
        if result is None:
            continue

        # If status indicates no data, don't include in merge
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
    """Get list of dependencies that should be included in merge.

    Excludes dependencies without result or without silver_table since
    they have no data to merge.

    Note: SKIPPED status (due to resume) IS mergeable because the data
    already exists in the Silver table.

    Args:
        dependency_results: All dependency results.
        all_dependencies: All dependency configs.
        logger: Logger port for structured logging.

    Returns:
        List of DependencyConfig for dependencies that have data to merge.
    """
    mergeable: list[DependencyConfig] = []
    for dep_cfg in all_dependencies:
        result = dependency_results.get(dep_cfg.pipeline)

        # If no result, don't include in merge
        if result is None:
            logger.debug(
                "Excluding dependency from merge",
                dependency=dep_cfg.pipeline,
                reason="no_result",
            )
            continue

        # If no silver_table configured, can't read data
        if not dep_cfg.silver_table:
            logger.debug(
                "Excluding dependency from merge",
                dependency=dep_cfg.pipeline,
                reason="no_silver_table",
            )
            continue

        # Success and Skipped (resume) are mergeable
        if result.is_success or result.status == DependencyStatus.SKIPPED:
            mergeable.append(dep_cfg)
        else:
            logger.debug(
                "Excluding dependency from merge",
                dependency=dep_cfg.pipeline,
                status=result.status.value,
                reason="execution_failed_or_timed_out",
            )

    return mergeable
