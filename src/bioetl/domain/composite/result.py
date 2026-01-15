"""Composite pipeline result models.

Defines immutable result objects for composite pipeline execution:
- EnrichmentResult: Result of a single enricher
- MergeResult: Result of merge operation
- CompositeResult: Complete composite pipeline result

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
    """Status of enrichment pipeline execution.

    Attributes:
        SUCCESS: All records enriched successfully.
        PARTIAL: Some records enriched, below hard threshold.
        FAILED: Above hard threshold or critical error.
        SKIPPED: Filter condition excluded all records.
        NOT_RUN: Pipeline not executed (e.g., resume scenario).
        TIMEOUT: Pipeline timed out before completion.
    """

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_RUN = "not_run"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class EnrichmentResult:
    """Result of a single enrichment pipeline execution.

    Immutable record of enricher execution outcome including
    counts, DQ metrics, and timing information.

    Attributes:
        enricher_name: Name of the enricher pipeline.
        status: Execution status.
        records_input: Number of keys provided for enrichment.
        records_enriched: Number of records successfully enriched.
        records_not_found: Number of keys not found in source.
        records_errored: Number of records with processing errors.
        dq_error_rate: Data quality error rate (0.0-1.0).
        duration_seconds: Total execution time.
        started_at: Timestamp when enricher started.
        completed_at: Timestamp when enricher completed.
        error_message: Error message if failed.

    Example:
        >>> result = EnrichmentResult(
        ...     enricher_name="crossref_publication",
        ...     status=EnrichmentStatus.SUCCESS,
        ...     records_input=100,
        ...     records_enriched=95,
        ...     records_not_found=3,
        ...     records_errored=2,
        ...     dq_error_rate=0.02,
        ...     duration_seconds=45.3,
        ... )
        >>> result.is_success
        True
        >>> result.enrichment_rate
        0.95
    """

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
        if self.dq_error_rate < 0.0 or self.dq_error_rate > 1.0:
            raise ValueError(
                f"dq_error_rate must be between 0.0 and 1.0, got {self.dq_error_rate}"
            )
        if self.duration_seconds < 0.0:
            raise ValueError(
                f"duration_seconds must be non-negative, got {self.duration_seconds}"
            )

    @property
    def is_success(self) -> bool:
        """Check if enrichment was successful or partially successful."""
        return self.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL)

    @property
    def enrichment_rate(self) -> float:
        """Calculate enrichment success rate.

        Returns:
            Ratio of enriched records to input records (0.0-1.0).
            Returns 0.0 if no input records.
        """
        if self.records_input == 0:
            return 0.0
        return self.records_enriched / self.records_input

    @property
    def not_found_rate(self) -> float:
        """Calculate not-found rate.

        Returns:
            Ratio of not-found records to input records (0.0-1.0).
        """
        if self.records_input == 0:
            return 0.0
        return self.records_not_found / self.records_input

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
        """Factory method for successful enrichment result."""
        return cls(
            enricher_name=enricher_name,
            status=EnrichmentStatus.SUCCESS,
            records_input=records_input,
            records_enriched=records_enriched,
            records_not_found=records_not_found,
            records_errored=0,
            dq_error_rate=0.0,
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
        """Factory method for failed enrichment result."""
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
        reason: str = "Filter condition excluded all records",
    ) -> EnrichmentResult:
        """Factory method for skipped enrichment result."""
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
        """Factory method for timeout enrichment result."""
        return cls(
            enricher_name=enricher_name,
            status=EnrichmentStatus.TIMEOUT,
            records_input=records_input,
            error_message=f"Timeout after {timeout_seconds}s",
            duration_seconds=timeout_seconds,
        )


@dataclass(frozen=True, slots=True)
class SeedResult:
    """Result of seed pipeline execution.

    Attributes:
        pipeline_name: Name of the seed pipeline.
        records_extracted: Number of records extracted.
        records_silver: Number of records written to Silver.
        keys_generated: Number of unique keys for enrichment.
        duration_seconds: Total execution time.
        started_at: Timestamp when seed started.
        completed_at: Timestamp when seed completed.
        resumed: True if this was a resumed run.
    """

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
    """Result of merge operation.

    Attributes:
        records_merged: Total records in merged output.
        records_from_seed: Records originating from seed.
        records_enriched: Records with at least one enrichment.
        records_fully_enriched: Records with all required enrichments.
        sources_used: List of sources that contributed data.
        field_coverage: Mapping of field to percentage populated.
        duration_seconds: Merge operation duration.
        output_silver_path: Path to merged Silver table.
        output_gold_path: Path to merged Gold table.
        lineage_summary: Summary of lineage metadata.
    """

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
        if self.records_merged == 0:
            return 0.0
        return self.records_enriched / self.records_merged

    @property
    def full_enrichment_rate(self) -> float:
        """Calculate fully enriched rate."""
        if self.records_merged == 0:
            return 0.0
        return self.records_fully_enriched / self.records_merged


@dataclass(frozen=True, slots=True)
class CompositeResult:
    """Complete result of composite pipeline execution.

    Aggregates results from seed, all enrichers, and merge operations.
    Provides summary statistics and overall status.

    Attributes:
        composite_name: Name of the composite pipeline.
        composite_run_id: Unique identifier for this run.
        seed_result: Result from seed pipeline.
        enrichment_results: Mapping of enricher name to result.
        merge_result: Result from merge operation.
        total_duration_seconds: Total composite execution time.
        started_at: Timestamp when composite started.
        completed_at: Timestamp when composite completed.
        lineage: Complete lineage metadata.

    Example:
        >>> result = CompositeResult(
        ...     composite_name="composite_publication",
        ...     composite_run_id="uuid",
        ...     seed_result=seed_result,
        ...     enrichment_results={"crossref": crossref_result},
        ...     merge_result=merge_result,
        ... )
        >>> result.is_success
        True
        >>> result.required_enrichers_succeeded
        True
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
    # Tracking which enrichers were required
    _required_enrichers: frozenset[str] = field(default_factory=frozenset)

    @property
    def is_success(self) -> bool:
        """Check if composite completed successfully.

        Success requires:
        - Seed successful
        - All required enrichers successful
        - Merge successful
        """
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
        for enricher_name in self._required_enrichers:
            result = self.enrichment_results.get(enricher_name)
            if result is None or not result.is_success:
                return False
        return True

    @property
    def successful_enrichers(self) -> list[str]:
        """List of enrichers that succeeded."""
        return [
            name for name, result in self.enrichment_results.items()
            if result.is_success
        ]

    @property
    def failed_enrichers(self) -> list[str]:
        """List of enrichers that failed."""
        return [
            name for name, result in self.enrichment_results.items()
            if result.status == EnrichmentStatus.FAILED
        ]

    @property
    def total_records_enriched(self) -> int:
        """Total records enriched across all enrichers."""
        return sum(
            r.records_enriched for r in self.enrichment_results.values()
        )

    def get_enricher_result(self, enricher_name: str) -> EnrichmentResult | None:
        """Get result for a specific enricher."""
        return self.enrichment_results.get(enricher_name)

    def summary(self) -> dict[str, object]:
        """Generate summary dictionary for logging/reporting."""
        return {
            "composite_name": self.composite_name,
            "composite_run_id": self.composite_run_id,
            "is_success": self.is_success,
            "seed_records": self.seed_result.records_silver,
            "enrichers_run": len(self.enrichment_results),
            "enrichers_succeeded": len(self.successful_enrichers),
            "enrichers_failed": len(self.failed_enrichers),
            "records_merged": self.merge_result.records_merged if self.merge_result else 0,
            "total_duration_seconds": self.total_duration_seconds,
        }
