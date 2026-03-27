"""Pure helper functions for runner enrichment summaries and warnings."""

from __future__ import annotations

from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus
from bioetl.domain.ports import LoggerPort


def log_enrichment_summary(
    enrichment_results: dict[str, EnrichmentResult],
    composite_name: str,
    logger: LoggerPort,
) -> None:
    """Log aggregated summary of enrichment results."""
    if not enrichment_results:
        return
    status_counts: dict[EnrichmentStatus, int] = dict.fromkeys(EnrichmentStatus, 0)
    failed_enrichers: list[str] = []
    successful_enrichers: list[str] = []
    not_run_enrichers: list[str] = []
    success_statuses = {EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL}
    failure_statuses = {EnrichmentStatus.FAILED, EnrichmentStatus.TIMEOUT}
    total_records_input = total_records_enriched = total_records_errored = 0

    for name, result in enrichment_results.items():
        total_records_input += result.records_input
        total_records_enriched += result.records_enriched
        total_records_errored += result.records_errored
        status_counts[result.status] += 1
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
    """Calculate whether optional enricher failures should be surfaced as warnings."""
    for name, result in enrichment_results.items():
        if name in required_enrichers:
            continue
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


__all__ = ["calculate_had_warnings", "log_enrichment_summary"]
