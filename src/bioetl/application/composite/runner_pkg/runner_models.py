"""Shared runtime data models for composite runner internals."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
    SeedResult,
)

__all__ = [
    "CompositeExecutionContext",
    "CompositeRuntimeConfig",
]


@dataclass(frozen=True, slots=True)
class CompositeRuntimeConfig:
    """Runtime configuration for composite pipeline execution."""

    resume: bool = False
    dry_run: bool = False
    enrich_only: tuple[str, ...] | None = None
    required_only: bool = False
    force_enricher: str | None = None
    seed_limit: int | None = None
    use_cached_bronze: bool = False
    cached_bronze_path: str | None = None
    cached_bronze_date: str | None = None
    cached_bronze_enrichers: bool | None = None
    cached_bronze_dependencies: bool = False

    def __post_init__(self) -> None:
        """Normalize mutable values into immutable runtime fields."""
        if isinstance(self.enrich_only, list):
            object.__setattr__(self, "enrich_only", tuple(self.enrich_only))


@dataclass(frozen=True, slots=True)
class CompositeExecutionContext:
    """Named stage outputs passed into final result assembly."""

    seed_result: SeedResult
    dependency_results: dict[str, DependencyResult]
    enrichment_results: dict[str, EnrichmentResult]
    merge_result: MergeResult | None
