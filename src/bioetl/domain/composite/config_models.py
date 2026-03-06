"""Composite pipeline configuration dataclass models."""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    EnricherCardinality,
)
from bioetl.domain.composite.config_merge import ColumnGroupConfig
from bioetl.domain.composite.config_validators import (
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
        if isinstance(self.output_keys, list):
            object.__setattr__(self, "output_keys", tuple(self.output_keys))
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
        if isinstance(self.join_keys, list):
            object.__setattr__(self, "join_keys", tuple(self.join_keys))
        if isinstance(self.filter_fields, list):
            object.__setattr__(self, "filter_fields", tuple(self.filter_fields))
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
        return self.join_keys[0]

    @property
    def uses_seed_keys(self) -> bool:
        return self.key_source is None or self.key_source == "seed"

    @property
    def effective_filter_fields(self) -> tuple[str, ...]:
        if self.filter_fields:
            return self.filter_fields
        if self.filter_field:
            return (self.filter_field,)
        return (self.join_keys[0],)

    @property
    def is_multi_field_filter(self) -> bool:
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
        if isinstance(self.join_keys, list):
            object.__setattr__(self, "join_keys", tuple(self.join_keys))
        if isinstance(self.fallback_strategy, str):
            object.__setattr__(
                self,
                "fallback_strategy",
                FallbackStrategy.from_string(self.fallback_strategy),
            )
        if isinstance(self.cardinality, str):
            object.__setattr__(
                self,
                "cardinality",
                EnricherCardinality.from_string(self.cardinality),
            )
        if isinstance(self.aggregation, dict):
            object.__setattr__(
                self,
                "aggregation",
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
        return self.join_keys[0]

    @property
    def has_fallback_keys(self) -> bool:
        return len(self.join_keys) > 1

    @property
    def is_many_to_one(self) -> bool:
        return self.cardinality == EnricherCardinality.MANY_TO_ONE


def _coerce_to_tuple(obj: object, attr: str) -> None:
    val = getattr(obj, attr, None)
    if val is not None and isinstance(val, list):
        object.__setattr__(obj, attr, tuple(val))


def _coerce_column_groups(obj: object, attr: str) -> None:
    val = getattr(obj, attr, None)
    if val is not None and isinstance(val, list):
        object.__setattr__(
            obj,
            attr,
            tuple(
                ColumnGroupConfig(**group) if isinstance(group, dict) else group
                for group in val
            ),
        )


@dataclass(frozen=True, slots=True)
class LayerColumnConfig:
    columns: tuple[str, ...] | None = None
    column_groups: tuple[ColumnGroupConfig, ...] | None = None
    include_groups: tuple[str, ...] | None = None
    exclude_fields: tuple[str, ...] | None = None
    rename_fields: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _coerce_to_tuple(self, "columns")
        _coerce_to_tuple(self, "include_groups")
        _coerce_to_tuple(self, "exclude_fields")
        _coerce_column_groups(self, "column_groups")
        if not isinstance(self.rename_fields, dict):
            object.__setattr__(self, "rename_fields", dict(self.rename_fields))
        self._validate()

    def _validate(self) -> None:
        modes = sum(
            [
                self.columns is not None,
                self.include_groups is not None,
                self.column_groups is not None,
            ]
        )
        if modes > 1:
            raise ValueError(
                "LayerColumnConfig: only one of columns/include_groups/column_groups allowed"
            )


@dataclass(frozen=True, slots=True)
class DataSchemaConfig:
    column_groups: tuple[ColumnGroupConfig, ...] = ()
    silver: LayerColumnConfig | None = None
    gold: LayerColumnConfig | None = None

    def __post_init__(self) -> None:
        _coerce_column_groups(self, "column_groups")
        if isinstance(self.silver, dict):
            object.__setattr__(self, "silver", LayerColumnConfig(**self.silver))
        if isinstance(self.gold, dict):
            object.__setattr__(self, "gold", LayerColumnConfig(**self.gold))

    def get_layer_groups(self, layer: str) -> tuple[ColumnGroupConfig, ...]:
        """Return layer-specific groups, falling back to top-level groups."""
        layer_config: LayerColumnConfig | None = getattr(self, layer, None)
        if layer_config and layer_config.column_groups:
            return layer_config.column_groups
        return self.column_groups

    def should_include_group(self, layer: str, group_name: str) -> bool:
        """Check whether a column group is included for the given layer."""
        layer_config = getattr(self, layer, None)
        if not layer_config or not layer_config.include_groups:
            return True
        return group_name in layer_config.include_groups


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
        if isinstance(self.enricher_pairings, list):
            object.__setattr__(self, "enricher_pairings", tuple(self.enricher_pairings))
        self._validate()

    def _validate(self) -> None:
        self._validate_thresholds()
        self._validate_tolerances()

    def _validate_thresholds(self) -> None:
        if self.warning_threshold < 1:
            raise ValueError(
                f"warning_threshold must be >= 1, got {self.warning_threshold}"
            )
        if self.error_threshold < 2:
            raise ValueError(
                f"error_threshold must be >= 2, got {self.error_threshold}"
            )
        if self.warning_threshold >= self.error_threshold:
            raise ValueError("warning_threshold must be < error_threshold")
        if self.quarantine_threshold < 1:
            raise ValueError(
                f"quarantine_threshold must be >= 1, got {self.quarantine_threshold}"
            )

    def _validate_tolerances(self) -> None:
        if not 0.0 < self.fuzzy_threshold <= 1.0:
            raise ValueError(
                f"fuzzy_threshold must be in (0.0, 1.0], got {self.fuzzy_threshold}"
            )
        if not 0.0 < self.numeric_tolerance <= 1.0:
            raise ValueError(
                f"numeric_tolerance must be in (0.0, 1.0], got {self.numeric_tolerance}"
            )

    def get_pairing(self, enricher_pipeline: str) -> EnricherFieldPairing | None:
        """Look up field pairing config for the given enricher pipeline."""
        for pairing in self.enricher_pairings:
            if pairing.enricher_pipeline == enricher_pipeline:
                return pairing
        return None
