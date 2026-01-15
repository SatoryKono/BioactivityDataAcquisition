"""Composite pipeline configuration models.

Defines immutable configuration objects for composite pipelines:
- SeedConfig: Seed pipeline configuration
- EnricherConfig: Single enricher configuration
- MergeConfig: Merge operation configuration
- CompositeConfig: Complete composite pipeline configuration

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.composite.strategy import (
    ConflictResolution,
    FallbackStrategy,
    MergeStrategy,
)

if TYPE_CHECKING:
    pass


@dataclass(frozen=True, slots=True)
class SeedConfig:
    """Configuration for seed pipeline in a composite.

    The seed pipeline extracts primary entities that will be
    enriched by downstream pipelines.

    Attributes:
        pipeline: Name of the seed pipeline (e.g., "chembl_publication").
        output_keys: Keys to extract for enrichment (e.g., ["doi", "pmid"]).
        silver_table: Path to seed Silver table output.
        limit: Optional limit on records to extract.

    Example:
        >>> config = SeedConfig(
        ...     pipeline="chembl_publication",
        ...     output_keys=("document_id", "doi", "pmid"),
        ...     silver_table="silver/chembl/publication",
        ... )
    """

    pipeline: str
    output_keys: tuple[str, ...]
    silver_table: str
    limit: int | None = None

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.output_keys, list):
            object.__setattr__(self, "output_keys", tuple(self.output_keys))
        self._validate()

    def _validate(self) -> None:
        """Validate configuration invariants."""
        if not self.pipeline:
            raise ValueError("seed pipeline name cannot be empty")
        if not self.output_keys:
            raise ValueError("seed output_keys cannot be empty")
        if not self.silver_table:
            raise ValueError("seed silver_table cannot be empty")
        if self.limit is not None and self.limit <= 0:
            raise ValueError(f"seed limit must be positive, got {self.limit}")


@dataclass(frozen=True, slots=True)
class EnricherConfig:
    """Configuration for a single enrichment pipeline.

    Defines how an enricher joins with seed data and handles failures.

    Attributes:
        pipeline: Name of the enricher pipeline (e.g., "crossref_publication").
        join_keys: Keys to join on from seed (e.g., ("doi",) or ("doi", "pmid")).
            Multiple keys indicate fallback chain: try doi first, then pmid.
        required: If True, failure causes composite failure.
        filter_condition: SQL-like condition to filter keys before enrichment.
            Example: "pmid IS NOT NULL" skips records without pmid.
        timeout_seconds: Maximum time for enricher execution.
        fallback_strategy: Strategy when enricher fails.
        silver_table: Path to enricher Silver table (auto-generated if None).
        limit: Optional limit on records to enrich.

    Example:
        >>> config = EnricherConfig(
        ...     pipeline="crossref_publication",
        ...     join_keys=("doi",),
        ...     required=True,
        ...     timeout_seconds=600,
        ... )
    """

    pipeline: str
    join_keys: tuple[str, ...]
    required: bool = False
    filter_condition: str | None = None
    timeout_seconds: int = 600
    fallback_strategy: FallbackStrategy = FallbackStrategy.SKIP
    silver_table: str | None = None
    limit: int | None = None

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.join_keys, list):
            object.__setattr__(self, "join_keys", tuple(self.join_keys))
        if isinstance(self.fallback_strategy, str):
            object.__setattr__(
                self,
                "fallback_strategy",
                FallbackStrategy.from_string(self.fallback_strategy),
            )
        self._validate()

    def _validate(self) -> None:
        """Validate configuration invariants."""
        if not self.pipeline:
            raise ValueError("enricher pipeline name cannot be empty")
        if not self.join_keys:
            raise ValueError(f"enricher {self.pipeline} join_keys cannot be empty")
        if self.timeout_seconds <= 0:
            raise ValueError(
                f"enricher {self.pipeline} timeout_seconds must be positive, "
                f"got {self.timeout_seconds}"
            )
        if self.limit is not None and self.limit <= 0:
            raise ValueError(
                f"enricher {self.pipeline} limit must be positive, got {self.limit}"
            )

    @property
    def primary_join_key(self) -> str:
        """Get the primary (first) join key."""
        return self.join_keys[0]

    @property
    def has_fallback_keys(self) -> bool:
        """Check if fallback join keys are available."""
        return len(self.join_keys) > 1


@dataclass(frozen=True, slots=True)
class MergeConfig:
    """Configuration for merge step.

    Defines how enriched data is combined into a unified output.

    Attributes:
        strategy: Join strategy for merging (left_outer, inner, union).
        conflict_resolution: Strategy for field conflicts.
        output_silver_path: Path for merged Silver table.
        output_gold_path: Path for merged Gold table.
        field_priorities: Mapping of field to source priority list.
            Used with EXPLICIT_RULES conflict resolution.
            Example: {"title": ["chembl", "crossref"]}
        field_mappings: Mapping to rename fields during merge.
            Example: {"crossref_title": "title"}

    Example:
        >>> config = MergeConfig(
        ...     strategy=MergeStrategy.LEFT_OUTER,
        ...     conflict_resolution=ConflictResolution.SEED_PRIORITY,
        ...     output_silver_path="silver/composite/publication",
        ...     output_gold_path="gold/publication_enriched",
        ... )
    """

    strategy: MergeStrategy
    conflict_resolution: ConflictResolution
    output_silver_path: str
    output_gold_path: str
    field_priorities: dict[str, tuple[str, ...]] = field(default_factory=dict)
    field_mappings: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.strategy, str):
            object.__setattr__(
                self, "strategy", MergeStrategy.from_string(self.strategy)
            )
        if isinstance(self.conflict_resolution, str):
            object.__setattr__(
                self,
                "conflict_resolution",
                ConflictResolution.from_string(self.conflict_resolution),
            )
        # Convert list values in field_priorities to tuples
        if self.field_priorities:
            converted = {
                k: tuple(v) if isinstance(v, list) else v
                for k, v in self.field_priorities.items()
            }
            object.__setattr__(self, "field_priorities", converted)
        self._validate()

    def _validate(self) -> None:
        """Validate configuration invariants."""
        if not self.output_silver_path:
            raise ValueError("merge output_silver_path cannot be empty")
        if not self.output_gold_path:
            raise ValueError("merge output_gold_path cannot be empty")
        if (
            self.conflict_resolution == ConflictResolution.EXPLICIT_RULES
            and not self.field_priorities
        ):
            raise ValueError(
                "field_priorities required when using EXPLICIT_RULES conflict resolution"
            )

    def get_field_priority(self, field_name: str) -> tuple[str, ...] | None:
        """Get source priority order for a field.

        Args:
            field_name: Name of the field.

        Returns:
            Tuple of source names in priority order, or None if not configured.
        """
        return self.field_priorities.get(field_name)


@dataclass(frozen=True, slots=True)
class DQOverrideConfig:
    """DQ threshold overrides for a specific enricher.

    Allows customizing DQ thresholds per-enricher when defaults
    are too strict or lenient.

    Attributes:
        soft_fail_threshold: Override soft threshold (0.0-1.0).
        hard_fail_threshold: Override hard threshold (0.0-1.0).
    """

    soft_fail_threshold: float | None = None
    hard_fail_threshold: float | None = None

    def __post_init__(self) -> None:
        """Validate threshold values."""
        if (
            self.soft_fail_threshold is not None
            and not 0.0 <= self.soft_fail_threshold <= 1.0
        ):
            raise ValueError(
                f"soft_fail_threshold must be between 0.0 and 1.0, "
                f"got {self.soft_fail_threshold}"
            )
        if (
            self.hard_fail_threshold is not None
            and not 0.0 <= self.hard_fail_threshold <= 1.0
        ):
            raise ValueError(
                f"hard_fail_threshold must be between 0.0 and 1.0, "
                f"got {self.hard_fail_threshold}"
            )
        if (
            self.soft_fail_threshold is not None
            and self.hard_fail_threshold is not None
            and self.soft_fail_threshold >= self.hard_fail_threshold
        ):
            raise ValueError(
                "soft_fail_threshold must be less than hard_fail_threshold"
            )


@dataclass(frozen=True, slots=True)
class CompositeDQConfig:
    """Data quality configuration for composite pipelines.

    Extends standard DQConfig with per-enricher overrides.

    Attributes:
        soft_fail_threshold: Default soft threshold for composite.
        hard_fail_threshold: Default hard threshold for composite.
        enricher_overrides: Per-enricher DQ threshold overrides.
        required_fields: Fields required in final Gold output.
    """

    soft_fail_threshold: float = 0.10
    hard_fail_threshold: float = 0.30
    enricher_overrides: dict[str, DQOverrideConfig] = field(default_factory=dict)
    required_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.required_fields, list):
            object.__setattr__(self, "required_fields", tuple(self.required_fields))
        self._validate()

    def _validate(self) -> None:
        """Validate DQ configuration."""
        if not 0.0 <= self.soft_fail_threshold <= 1.0:
            raise ValueError(
                f"soft_fail_threshold must be between 0.0 and 1.0, "
                f"got {self.soft_fail_threshold}"
            )
        if not 0.0 <= self.hard_fail_threshold <= 1.0:
            raise ValueError(
                f"hard_fail_threshold must be between 0.0 and 1.0, "
                f"got {self.hard_fail_threshold}"
            )
        if self.soft_fail_threshold >= self.hard_fail_threshold:
            raise ValueError(
                "soft_fail_threshold must be less than hard_fail_threshold"
            )

    def get_enricher_soft_threshold(self, enricher_name: str) -> float:
        """Get effective soft threshold for an enricher."""
        override = self.enricher_overrides.get(enricher_name)
        if override and override.soft_fail_threshold is not None:
            return override.soft_fail_threshold
        return self.soft_fail_threshold

    def get_enricher_hard_threshold(self, enricher_name: str) -> float:
        """Get effective hard threshold for an enricher."""
        override = self.enricher_overrides.get(enricher_name)
        if override and override.hard_fail_threshold is not None:
            return override.hard_fail_threshold
        return self.hard_fail_threshold


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """Execution options for composite pipeline.

    Attributes:
        max_concurrency: Maximum concurrent enrichers.
        checkpoint_enabled: Enable checkpointing for resume.
        retry_max_attempts: Max retry attempts per enricher.
        retry_backoff_multiplier: Backoff multiplier for retries.
    """

    max_concurrency: int = 4
    checkpoint_enabled: bool = True
    retry_max_attempts: int = 3
    retry_backoff_multiplier: float = 2.0

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_concurrency <= 0:
            raise ValueError(
                f"max_concurrency must be positive, got {self.max_concurrency}"
            )
        if self.retry_max_attempts < 0:
            raise ValueError(
                f"retry_max_attempts must be non-negative, got {self.retry_max_attempts}"
            )
        if self.retry_backoff_multiplier <= 0:
            raise ValueError(
                f"retry_backoff_multiplier must be positive, "
                f"got {self.retry_backoff_multiplier}"
            )


@dataclass(frozen=True, slots=True)
class LineageConfig:
    """Configuration for lineage tracking.

    Attributes:
        track_field_sources: Track which source provided each field.
        track_timestamps: Include enrichment timestamps.
        track_status: Include per-record enrichment status.
    """

    track_field_sources: bool = True
    track_timestamps: bool = True
    track_status: bool = True


@dataclass(frozen=True, slots=True)
class CompositeConfig:
    """Complete composite pipeline configuration.

    Combines all configuration aspects: seed, enrichers, merge,
    DQ, execution options, and lineage tracking.

    This is the main configuration object loaded from YAML and
    used by CompositePipelineRunner.

    Attributes:
        name: Composite pipeline name (e.g., "composite_publication").
        version: Configuration version (semver).
        seed: Seed pipeline configuration.
        enrichers: Tuple of enricher configurations.
        merge: Merge step configuration.
        dq: Data quality configuration.
        execution: Execution options.
        lineage: Lineage tracking configuration.

    Example:
        >>> config = CompositeConfig(
        ...     name="composite_publication",
        ...     version="1.0.0",
        ...     seed=SeedConfig(...),
        ...     enrichers=(EnricherConfig(...), EnricherConfig(...)),
        ...     merge=MergeConfig(...),
        ... )
        >>> config.required_enrichers
        ('crossref_publication',)
    """

    name: str
    version: str
    seed: SeedConfig
    enrichers: tuple[EnricherConfig, ...]
    merge: MergeConfig
    dq: CompositeDQConfig = field(default_factory=CompositeDQConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    lineage: LineageConfig = field(default_factory=LineageConfig)

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.enrichers, list):
            object.__setattr__(self, "enrichers", tuple(self.enrichers))
        self._validate()

    def _validate(self) -> None:
        """Validate composite configuration."""
        if not self.name:
            raise ValueError("composite name cannot be empty")
        if not self.version:
            raise ValueError("composite version cannot be empty")
        if not self.enrichers:
            raise ValueError("composite must have at least one enricher")
        self._validate_join_keys()
        self._validate_unique_enrichers()

    def _validate_join_keys(self) -> None:
        """Validate that enricher join keys exist in seed output_keys."""
        seed_keys = set(self.seed.output_keys)
        for enricher in self.enrichers:
            for key in enricher.join_keys:
                if key not in seed_keys:
                    raise ValueError(
                        f"Enricher {enricher.pipeline} join_key '{key}' "
                        f"not found in seed output_keys: {self.seed.output_keys}"
                    )

    def _validate_unique_enrichers(self) -> None:
        """Validate that enricher pipeline names are unique."""
        names = [e.pipeline for e in self.enrichers]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate enricher pipelines: {set(duplicates)}")

    @property
    def required_enrichers(self) -> tuple[str, ...]:
        """Get names of required enrichers."""
        return tuple(e.pipeline for e in self.enrichers if e.required)

    @property
    def optional_enrichers(self) -> tuple[str, ...]:
        """Get names of optional enrichers."""
        return tuple(e.pipeline for e in self.enrichers if not e.required)

    @property
    def all_enricher_names(self) -> tuple[str, ...]:
        """Get names of all enrichers."""
        return tuple(e.pipeline for e in self.enrichers)

    def get_enricher(self, pipeline_name: str) -> EnricherConfig | None:
        """Get enricher config by pipeline name."""
        for enricher in self.enrichers:
            if enricher.pipeline == pipeline_name:
                return enricher
        return None

    @property
    def lock_key(self) -> str:
        """Generate lock key for composite pipeline."""
        return f"composite:{self.name}"

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "seed": {
                "pipeline": self.seed.pipeline,
                "output_keys": list(self.seed.output_keys),
                "silver_table": self.seed.silver_table,
            },
            "enrichers": [
                {
                    "pipeline": e.pipeline,
                    "join_keys": list(e.join_keys),
                    "required": e.required,
                    "timeout_seconds": e.timeout_seconds,
                }
                for e in self.enrichers
            ],
            "merge": {
                "strategy": self.merge.strategy.value,
                "conflict_resolution": self.merge.conflict_resolution.value,
                "output_silver_path": self.merge.output_silver_path,
                "output_gold_path": self.merge.output_gold_path,
            },
        }
