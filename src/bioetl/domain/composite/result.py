"""Composite pipeline result models.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.composite.lineage import LineageMetadata


class EnrichmentStatus(str, Enum):
    """Status of enrichment pipeline execution."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_RUN = "not_run"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class EnrichmentResult:
    """Result of a single enrichment pipeline execution."""

    enricher_name: str
    status: EnrichmentStatus
    records_input: int = 0
    records_enriched: int = 0
    records_not_found: int = 0
    records_errored: int = 0
    dq_error_rate: float = 0.0
    duration_seconds: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate result invariants."""
        if not 0.0 <= self.dq_error_rate <= 1.0:
            raise ValueError(f"dq_error_rate must be 0.0-1.0, got {self.dq_error_rate}")
        if self.duration_seconds < 0.0:
            raise ValueError(
                f"duration_seconds must be >= 0, got {self.duration_seconds}"
            )

    @property
    def is_success(self) -> bool:
        """Check if enrichment was successful or partially successful."""
        return self.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL)

    @property
    def enrichment_rate(self) -> float:
        """Calculate enrichment success rate (0.0-1.0)."""
        return self.records_enriched / self.records_input if self.records_input else 0.0

    @property
    def not_found_rate(self) -> float:
        """Calculate not-found rate (0.0-1.0)."""
        return (
            self.records_not_found / self.records_input if self.records_input else 0.0
        )

    @classmethod
    def success(
        cls,
        enricher_name: str,
        records_input: int,
        records_enriched: int,
        records_not_found: int = 0,
        duration_seconds: float = 0.0,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> EnrichmentResult:
        """Factory for successful enrichment result."""
        return cls(
            enricher_name=enricher_name,
            status=EnrichmentStatus.SUCCESS,
            records_input=records_input,
            records_enriched=records_enriched,
            records_not_found=records_not_found,
            duration_seconds=duration_seconds,
            started_at=started_at,
            completed_at=completed_at,
        )

    @classmethod
    def failed(
        cls,
        enricher_name: str,
        error_message: str,
        records_input: int = 0,
        duration_seconds: float = 0.0,
    ) -> EnrichmentResult:
        """Factory for failed enrichment result."""
        return cls(
            enricher_name=enricher_name,
            status=EnrichmentStatus.FAILED,
            records_input=records_input,
            error_message=error_message,
            duration_seconds=duration_seconds,
        )

    @classmethod
    def skipped(
        cls,
        enricher_name: str,
        reason: str = "Filter excluded all records",
    ) -> EnrichmentResult:
        """Factory for skipped enrichment result."""
        return cls(
            enricher_name=enricher_name,
            status=EnrichmentStatus.SKIPPED,
            error_message=reason,
        )

    @classmethod
    def timeout(
        cls,
        enricher_name: str,
        timeout_seconds: float,
        records_input: int = 0,
    ) -> EnrichmentResult:
        """Factory for timeout enrichment result."""
        return cls(
            enricher_name=enricher_name,
            status=EnrichmentStatus.TIMEOUT,
            records_input=records_input,
            error_message=f"Timeout after {timeout_seconds}s",
            duration_seconds=timeout_seconds,
        )

    @classmethod
    def not_run(
        cls,
        enricher_name: str,
        reason: str = "Pipeline not executed (required_only mode)",
    ) -> EnrichmentResult:
        """Factory for not-run enrichment result.

        Used when an enricher is intentionally not executed,
        for example due to required_only mode or explicit exclusion.

        Args:
            enricher_name: Name of the enricher pipeline.
            reason: Human-readable reason why pipeline was not run.

        Returns:
            EnrichmentResult with NOT_RUN status.
        """
        return cls(
            enricher_name=enricher_name,
            status=EnrichmentStatus.NOT_RUN,
            error_message=reason,
        )


@dataclass(frozen=True, slots=True)
class SeedResult:
    """Result of seed pipeline execution."""

    pipeline_name: str
    records_extracted: int = 0
    records_silver: int = 0
    keys_generated: int = 0
    duration_seconds: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    resumed: bool = False

    @property
    def is_success(self) -> bool:
        """Check if seed was successful."""
        return self.records_silver > 0 or self.resumed


@dataclass(frozen=True, slots=True)
class MergeResult:
    """Result of merge operation."""

    records_merged: int = 0
    records_from_seed: int = 0
    records_enriched: int = 0
    records_fully_enriched: int = 0
    sources_used: tuple[str, ...] = ()
    field_coverage: dict[str, float] = field(default_factory=dict)
    duration_seconds: float = 0.0
    output_silver_path: str | None = None
    output_gold_path: str | None = None
    lineage_summary: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.sources_used, list):
            object.__setattr__(self, "sources_used", tuple(self.sources_used))

    @property
    def enrichment_rate(self) -> float:
        """Calculate overall enrichment rate."""
        return (
            self.records_enriched / self.records_merged if self.records_merged else 0.0
        )


@dataclass(frozen=True, slots=True)
class CompositeResult:
    """Complete result of composite pipeline execution.

    Attributes:
        composite_name: Name of the composite pipeline.
        composite_run_id: Unique run identifier.
        seed_result: Result of seed pipeline execution.
        enrichment_results: Results per enricher (keyed by pipeline name).
        merge_result: Result of merge operation (None if not completed).
        total_duration_seconds: Total execution time.
        started_at: Execution start timestamp.
        completed_at: Execution end timestamp.
        lineage: Optional lineage metadata.
        had_warnings: True if any optional enrichers failed but pipeline completed.
            This indicates "completed with warnings" status - the pipeline succeeded
            but some non-required enrichments did not complete successfully.
        _required_enrichers: Internal set of required enricher names.
    """

    composite_name: str
    composite_run_id: str
    seed_result: SeedResult
    enrichment_results: dict[str, EnrichmentResult] = field(default_factory=dict)
    merge_result: MergeResult | None = None
    total_duration_seconds: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    lineage: LineageMetadata | None = None
    had_warnings: bool = False
    _required_enrichers: frozenset[str] = field(default_factory=frozenset)

    @property
    def is_success(self) -> bool:
        """Check if composite completed successfully."""
        if not self.seed_result.is_success:
            return False
        if not self.required_enrichers_succeeded:
            return False
        if self.merge_result is None:
            return False
        return self.merge_result.records_merged > 0

    @property
    def required_enrichers_succeeded(self) -> bool:
        """Check if all required enrichers succeeded."""
        for name in self._required_enrichers:
            result = self.enrichment_results.get(name)
            if result is None or not result.is_success:
                return False
        return True

    @property
    def successful_enrichers(self) -> list[str]:
        """List of enrichers that succeeded."""
        return [n for n, r in self.enrichment_results.items() if r.is_success]

    @property
    def failed_enrichers(self) -> list[str]:
        """List of enrichers that failed."""
        return [
            n
            for n, r in self.enrichment_results.items()
            if r.status == EnrichmentStatus.FAILED
        ]

    @property
    def skipped_enrichers(self) -> list[str]:
        """List of enrichers that were skipped (filter excluded all records)."""
        return [
            n
            for n, r in self.enrichment_results.items()
            if r.status == EnrichmentStatus.SKIPPED
        ]

    @property
    def not_run_enrichers(self) -> list[str]:
        """List of enrichers that were not run (e.g., required_only mode)."""
        return [
            n
            for n, r in self.enrichment_results.items()
            if r.status == EnrichmentStatus.NOT_RUN
        ]

    @property
    def optional_failed_enrichers(self) -> list[str]:
        """List of optional enrichers that failed.

        These are enrichers that failed but are not required,
        so the pipeline can still complete successfully.
        """
        return [
            n
            for n, r in self.enrichment_results.items()
            if r.status == EnrichmentStatus.FAILED and n not in self._required_enrichers
        ]

    @property
    def total_records_enriched(self) -> int:
        """Total records enriched across all enrichers."""
        return sum(r.records_enriched for r in self.enrichment_results.values())

    def summary(self) -> dict[str, object]:
        """Generate summary dictionary for logging/reporting."""
        return {
            "composite_name": self.composite_name,
            "composite_run_id": self.composite_run_id,
            "is_success": self.is_success,
            "had_warnings": self.had_warnings,
            "seed_records": self.seed_result.records_silver,
            "enrichers_run": len(self.enrichment_results),
            "enrichers_succeeded": len(self.successful_enrichers),
            "enrichers_failed": len(self.failed_enrichers),
            "enrichers_skipped": len(self.skipped_enrichers),
            "enrichers_not_run": len(self.not_run_enrichers),
            "optional_failures": self.optional_failed_enrichers or None,
            "records_merged": self.merge_result.records_merged
            if self.merge_result
            else 0,
            "total_duration_seconds": self.total_duration_seconds,
        }
