"""Composite run aggregate result model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.composite.result_enrichment import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.result_merge import MergeResult
from bioetl.domain.composite.result_seed_dependency import (
    DependencyResult,
    DependencyStatus,
    SeedResult,
)
from bioetl.domain.immutability import freeze_fields

if TYPE_CHECKING:
    from bioetl.domain.composite.lineage import CompositeLineageMetadata

__all__ = ["CompositeResult"]


@dataclass(frozen=True, slots=True)
class CompositeResult:
    """Complete result of composite pipeline execution."""

    composite_name: str
    composite_run_id: str
    seed_result: SeedResult
    dependency_results: dict[str, DependencyResult] = field(default_factory=dict)
    enrichment_results: dict[str, EnrichmentResult] = field(default_factory=dict)
    merge_result: MergeResult | None = None
    total_duration_seconds: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    lineage: CompositeLineageMetadata | None = None
    had_warnings: bool = False
    original_run_id: str | None = None
    _required_enrichers: frozenset[str] = field(default_factory=frozenset)
    _required_dependencies: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Freeze result maps so callers cannot mutate composite state."""
        if not isinstance(self._required_enrichers, frozenset):
            object.__setattr__(
                self, "_required_enrichers", frozenset(self._required_enrichers)
            )
        if not isinstance(self._required_dependencies, frozenset):
            object.__setattr__(
                self, "_required_dependencies", frozenset(self._required_dependencies)
            )
        freeze_fields(self, ("dependency_results", "enrichment_results"))

    @property
    def is_success(self) -> bool:
        """Check if composite completed successfully."""
        if not self.seed_result.is_success:
            return False
        if not self.required_dependencies_succeeded:
            return False
        if not self.required_enrichers_succeeded:
            return False
        if self.merge_result is None:
            return False
        return self.merge_result.records_merged > 0

    @property
    def required_dependencies_succeeded(self) -> bool:
        """Check if all required dependencies succeeded."""
        for name in self._required_dependencies:
            result = self.dependency_results.get(name)
            if result is None or not result.is_success:
                return False
        return True

    @property
    def required_enrichers_succeeded(self) -> bool:
        """Check if all required enrichers succeeded."""
        for name in self._required_enrichers:
            result = self.enrichment_results.get(name)
            if result is None or not result.is_success:
                return False
        return True

    @property
    def successful_dependencies(self) -> list[str]:
        """List of dependencies that succeeded."""
        return [
            name
            for name, result in self.dependency_results.items()
            if result.is_success
        ]

    @property
    def failed_dependencies(self) -> list[str]:
        """List of dependencies that failed."""
        return [
            name
            for name, result in self.dependency_results.items()
            if result.status == DependencyStatus.FAILED
        ]

    @property
    def successful_enrichers(self) -> list[str]:
        """List of enrichers that succeeded."""
        return [
            name
            for name, result in self.enrichment_results.items()
            if result.is_success
        ]

    @property
    def failed_enrichers(self) -> list[str]:
        """List of enrichers that failed."""
        return [
            name
            for name, result in self.enrichment_results.items()
            if result.status == EnrichmentStatus.FAILED
        ]

    @property
    def skipped_enrichers(self) -> list[str]:
        """List of enrichers that were skipped."""
        return [
            name
            for name, result in self.enrichment_results.items()
            if result.status == EnrichmentStatus.SKIPPED
        ]

    @property
    def not_run_enrichers(self) -> list[str]:
        """List of enrichers that were not run."""
        return [
            name
            for name, result in self.enrichment_results.items()
            if result.status == EnrichmentStatus.NOT_RUN
        ]

    @property
    def optional_failed_enrichers(self) -> list[str]:
        """List of optional enrichers that failed."""
        return [
            name
            for name, result in self.enrichment_results.items()
            if result.status == EnrichmentStatus.FAILED
            and name not in self._required_enrichers
        ]

    @property
    def total_records_enriched(self) -> int:
        """Total records enriched across all enrichers."""
        return sum(
            result.records_enriched for result in self.enrichment_results.values()
        )

    def summary(self) -> dict[str, object]:
        """Generate summary dictionary for logging/reporting."""
        result: dict[str, object] = {
            "composite_name": self.composite_name,
            "composite_run_id": self.composite_run_id,
            "is_success": self.is_success,
            "had_warnings": self.had_warnings,
            "seed_records": self.seed_result.records_silver,
            "dependencies_run": len(self.dependency_results),
            "dependencies_succeeded": len(self.successful_dependencies),
            "dependencies_failed": len(self.failed_dependencies),
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
        if self.original_run_id is not None:
            result["original_run_id"] = self.original_run_id
        return result
