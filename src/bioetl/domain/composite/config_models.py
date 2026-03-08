"""Composite pipeline configuration dataclass models."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    EnricherCardinality,
)
from bioetl.domain.composite.config_schema import DataSchemaConfig, LayerColumnConfig
from bioetl.domain.composite.config_validators import (
    _coerce_to_tuple,
    _coerce_to_typed_tuple,
    _require_non_empty,
    _validate_positive,
    _validate_positive_limit,
)
from bioetl.domain.composite.cross_validation import EnricherFieldPairing
from bioetl.domain.composite.strategy import FallbackStrategy

__all__ = [
    "CrossValidationConfig",
    "DataSchemaConfig",
    "DependencyConfig",
    "EnricherConfig",
    "LayerColumnConfig",
    "SeedConfig",
]


@dataclass(frozen=True, slots=True)
class SeedConfig:
    """Seed pipeline settings."""

    pipeline: str
    output_keys: tuple[str, ...]
    silver_table: str
    limit: int | None = None

    def __post_init__(self) -> None:
        _coerce_to_tuple(self, "output_keys")
        self._validate()

    def _validate(self) -> None:
        _require_non_empty(self.pipeline, "seed pipeline name")
        _require_non_empty(self.output_keys, "seed output_keys")
        _require_non_empty(self.silver_table, "seed silver_table")
        _validate_positive_limit(self.limit, "seed")


@dataclass(frozen=True, slots=True)
class DependencyConfig:
    """Dependency pipeline settings for composite joins."""

    pipeline: str
    join_keys: tuple[str, ...]
    required: bool = False
    timeout_seconds: int = 600
    silver_table: str | None = None
    key_source: str | None = None
    filter_field: str | None = None
    filter_fields: tuple[str, ...] | None = None
    key_filter: str | None = None

    def __post_init__(self) -> None:
        _coerce_to_tuple(self, "join_keys")
        _coerce_to_tuple(self, "filter_fields")
        self._validate()

    def _validate(self) -> None:
        _require_non_empty(self.pipeline, "dependency pipeline name")
        _require_non_empty(self.join_keys, f"dependency {self.pipeline} join_keys")
        _validate_positive(
            self.timeout_seconds, f"dependency {self.pipeline} timeout_seconds"
        )
        if self.filter_fields and self.filter_field:
            raise ValueError(
                f"Dependency {self.pipeline}: filter_fields and filter_field "
                "are mutually exclusive. Use filter_fields for multi-field filtering."
            )

    @property
    def primary_join_key(self) -> str:
        """Return the first join key used as the primary filter field."""
        return self.join_keys[0]

    @property
    def uses_seed_keys(self) -> bool:
        """Return True if this dependency uses seed pipeline keys for filtering."""
        return self.key_source is None or self.key_source == "seed"

    @property
    def effective_filter_fields(self) -> tuple[str, ...]:
        """Return the resolved set of filter fields for this dependency.

        Resolves precedence: ``filter_fields`` > ``filter_field`` > first join key.
        """
        if self.filter_fields:
            return self.filter_fields
        if self.filter_field:
            return (self.filter_field,)
        return (self.join_keys[0],)

    @property
    def is_multi_field_filter(self) -> bool:
        """Return True if more than one effective filter field is active."""
        return len(self.effective_filter_fields) > 1


@dataclass(frozen=True, slots=True)
class EnricherConfig:
    """Enricher pipeline settings for composite joins."""

    pipeline: str
    join_keys: tuple[str, ...]
    required: bool = False
    filter_condition: str | None = None
    timeout_seconds: int = 600
    fallback_strategy: FallbackStrategy = FallbackStrategy.SKIP
    silver_table: str | None = None
    limit: int | None = None
    cardinality: EnricherCardinality = EnricherCardinality.ONE_TO_ONE
    aggregation: AggregationConfig | None = None

    def __post_init__(self) -> None:
        _coerce_to_tuple(self, "join_keys")
        if isinstance(self.fallback_strategy, str):
            object.__setattr__(
                self, "fallback_strategy",
                FallbackStrategy.from_string(self.fallback_strategy),
            )
        if isinstance(self.cardinality, str):
            object.__setattr__(
                self, "cardinality",
                EnricherCardinality.from_string(self.cardinality),
            )
        if isinstance(self.aggregation, dict):
            object.__setattr__(
                self, "aggregation",
                AggregationConfig(**self.aggregation),
            )
        self._validate()

    def _validate(self) -> None:
        _require_non_empty(self.pipeline, "enricher pipeline name")
        _require_non_empty(self.join_keys, f"enricher {self.pipeline} join_keys")
        _validate_positive(
            self.timeout_seconds, f"enricher {self.pipeline} timeout_seconds"
        )
        _validate_positive_limit(self.limit, f"enricher {self.pipeline}")
        if (
            self.cardinality == EnricherCardinality.MANY_TO_ONE
            and self.aggregation is None
        ):
            raise ValueError(
                f"Enricher '{self.pipeline}' with cardinality=many_to_one requires aggregation config"
            )

    @property
    def primary_join_key(self) -> str:
        """Return the first join key used as the primary enrichment join field."""
        return self.join_keys[0]

    @property
    def has_fallback_keys(self) -> bool:
        """Return True if secondary join keys are available for fallback matching."""
        return len(self.join_keys) > 1

    @property
    def is_many_to_one(self) -> bool:
        """Return True if this enricher has many-to-one cardinality (requires aggregation)."""
        return self.cardinality == EnricherCardinality.MANY_TO_ONE


def _validate_cross_validation_thresholds(
    warning_threshold: int,
    error_threshold: int,
    quarantine_threshold: int,
) -> None:
    if warning_threshold < 1:
        raise ValueError(
            f"warning_threshold must be >= 1, got {warning_threshold}"
        )
    if error_threshold < 2:
        raise ValueError(f"error_threshold must be >= 2, got {error_threshold}")
    if warning_threshold >= error_threshold:
        raise ValueError("warning_threshold must be < error_threshold")
    if quarantine_threshold < 1:
        raise ValueError(
            f"quarantine_threshold must be >= 1, got {quarantine_threshold}"
        )


def _validate_cross_validation_tolerances(
    fuzzy_threshold: float,
    numeric_tolerance: float,
) -> None:
    if not 0.0 < fuzzy_threshold <= 1.0:
        raise ValueError(
            f"fuzzy_threshold must be in (0.0, 1.0], got {fuzzy_threshold}"
        )
    if not 0.0 < numeric_tolerance <= 1.0:
        raise ValueError(
            f"numeric_tolerance must be in (0.0, 1.0], got {numeric_tolerance}"
        )


@dataclass(frozen=True, slots=True)
class CrossValidationConfig:
    """Configuration for cross-enricher data validation."""

    enabled: bool = True
    warning_threshold: int = 1
    error_threshold: int = 2
    quarantine_threshold: int = 2
    fuzzy_threshold: float = 0.8
    numeric_tolerance: float = 0.10
    enricher_pairings: tuple[EnricherFieldPairing, ...] = ()

    def __post_init__(self) -> None:
        _coerce_to_typed_tuple(self, "enricher_pairings", EnricherFieldPairing)
        self._validate()

    def _validate(self) -> None:
        _validate_cross_validation_thresholds(
            self.warning_threshold,
            self.error_threshold,
            self.quarantine_threshold,
        )
        _validate_cross_validation_tolerances(
            self.fuzzy_threshold,
            self.numeric_tolerance,
        )

    def get_pairing(self, enricher_pipeline: str) -> EnricherFieldPairing | None:
        """Look up field pairing config for the given enricher pipeline.

        Args:
            enricher_pipeline: Pipeline name to look up in the enricher_pairings list.

        Returns:
            Matching EnricherFieldPairing if found, otherwise None.
        """
        for pairing in self.enricher_pairings:
            if pairing.enricher_pipeline == enricher_pipeline:
                return pairing
        return None
