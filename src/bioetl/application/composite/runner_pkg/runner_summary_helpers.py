"""Pure helper functions for runner enrichment summaries and warnings."""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus
from bioetl.domain.ports import LoggerPort


@dataclass(slots=True)
class EnrichmentSummary:
    """Aggregated enrichment result summary for runner logging."""

    status_counts: dict[EnrichmentStatus, int] = field(
        default_factory=lambda: dict.fromkeys(EnrichmentStatus, 0)
    )
    failed_enrichers: list[str] = field(default_factory=list)
    successful_enrichers: list[str] = field(default_factory=list)
    not_run_enrichers: list[str] = field(default_factory=list)
    total_records_input: int = 0
    total_records_enriched: int = 0
    total_records_errored: int = 0


_SUCCESS_STATUSES = frozenset({EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL})
_FAILURE_STATUSES = frozenset({EnrichmentStatus.FAILED, EnrichmentStatus.TIMEOUT})


def _record_enricher_outcome(
    summary: EnrichmentSummary,
    *,
    name: str,
    result: EnrichmentResult,
) -> None:
    """Apply one enricher result to the summary accumulator."""
    summary.total_records_input += result.records_input
    summary.total_records_enriched += result.records_enriched
    summary.total_records_errored += result.records_errored
    summary.status_counts[result.status] += 1
    if result.status in _SUCCESS_STATUSES:
        summary.successful_enrichers.append(name)
    elif result.status in _FAILURE_STATUSES:
        summary.failed_enrichers.append(name)
    elif result.status == EnrichmentStatus.NOT_RUN:
        summary.not_run_enrichers.append(name)


def _summarize_enrichment_results(
    enrichment_results: dict[str, EnrichmentResult],
) -> EnrichmentSummary:
    """Build an aggregated summary for enrichment-result logging."""
    summary = EnrichmentSummary()
    for name, result in enrichment_results.items():
        _record_enricher_outcome(summary, name=name, result=result)
    return summary


def log_enrichment_summary(
    enrichment_results: dict[str, EnrichmentResult],
    composite_name: str,
    logger: LoggerPort,
) -> None:
    """Log aggregated summary of enrichment results."""
    if not enrichment_results:
        return
    summary = _summarize_enrichment_results(enrichment_results)

    logger.info(
        "Enrichment summary",
        composite=composite_name,
        total_enrichers=len(enrichment_results),
        success=summary.status_counts[EnrichmentStatus.SUCCESS],
        partial=summary.status_counts[EnrichmentStatus.PARTIAL],
        failed=summary.status_counts[EnrichmentStatus.FAILED],
        skipped=summary.status_counts[EnrichmentStatus.SKIPPED],
        timeout=summary.status_counts[EnrichmentStatus.TIMEOUT],
        not_run=summary.status_counts[EnrichmentStatus.NOT_RUN],
        successful_enrichers=summary.successful_enrichers,
        failed_enrichers=summary.failed_enrichers or None,
        not_run_enrichers=summary.not_run_enrichers or None,
        total_records_input=summary.total_records_input,
        total_records_enriched=summary.total_records_enriched,
        total_records_errored=summary.total_records_errored,
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
