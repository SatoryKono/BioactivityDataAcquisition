"""Pipeline configuration object.

Defines the immutable PipelineConfig value object — the main domain
configuration for a single ETL pipeline run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from bioetl.domain.composite import ColumnGroupConfig, DataSchemaConfig
from bioetl.domain.config._converters import freeze_sequences, resolve_loading_strategy
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.config.table import TableConfig
from bioetl.domain.constants import DEFAULT_BATCH_SIZE, DEFAULT_CHECKPOINT_INTERVAL
from bioetl.domain.medallion import LoadingStrategy
from bioetl.domain.types import ScdConfig

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.models.filter import SourceProfile

__all__ = [
    "FieldCoercionPolicy",
    "FieldPolicyConfig",
    "PipelineConfig",
]

FieldCoercionPolicy = Literal["default", "no_string_coercion"]


@dataclass(frozen=True, slots=True)
class FieldPolicyConfig:
    """Explicit field-level policy override for pipeline runtime behavior."""

    field: str
    optional: bool | None = None
    empty_as_missing: bool | None = None
    coercion_policy: FieldCoercionPolicy | None = None
    boolean_true_values: tuple[str, ...] = ()
    boolean_false_values: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate and freeze normalized field-level policy settings."""
        true_values = tuple(
            value.strip().lower() for value in self.boolean_true_values
        )
        false_values = tuple(
            value.strip().lower() for value in self.boolean_false_values
        )
        object.__setattr__(self, "boolean_true_values", true_values)
        object.__setattr__(self, "boolean_false_values", false_values)
        overlap = set(true_values) & set(false_values)
        if overlap:
            overlap_values = ", ".join(sorted(overlap))
            raise ValueError(
                "boolean_true_values and boolean_false_values must not overlap; "
                f"got: {overlap_values}"
            )


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Immutable pipeline configuration.

    Contains static configuration that doesn't change during execution.
    Frozen dataclass ensures immutability after creation.

    This is the consolidated domain configuration object that combines
    identity, data quality, table, and processing settings.

    Table-related fields are stored in the nested ``table`` field
    (:class:`TableConfig`). Use ``config.table.<field>`` for direct
    access. Effective Silver/Gold table names are exposed as
    ``effective_silver_table`` and ``effective_gold_table`` with
    fallback to ``{provider}.{entity_type}``.
    """

    # Identity
    pipeline_name: str
    provider: str
    entity_type: str

    # Table configuration — single source of truth
    table: TableConfig

    # Processing
    silver_filters: SilverFilterConfig | None = None
    gold_filters: GoldFilterConfig | None = None
    batch_size: int = DEFAULT_BATCH_SIZE
    checkpoint_interval: int = DEFAULT_CHECKPOINT_INTERVAL
    fields: tuple[str, ...] = ()
    column_groups: tuple[ColumnGroupConfig, ...] = ()
    data_schema: DataSchemaConfig | None = None
    field_policy: tuple[FieldPolicyConfig, ...] = ()
    source_profile: SourceProfile | None = None

    # Data Quality
    dq: DQConfig = field(default_factory=DQConfig)

    # Transform versioning (lineage tracking)
    transform_version: str | None = None
    transform_steps: tuple[str, ...] = ()

    # Loading strategy (ADR-031)
    # - FULL_SCAN_ONLY: Each run performs full scan, checkpoint resume disabled
    # - None: Default incremental behavior with checkpoint resume
    loading_strategy: LoadingStrategy | str | None = None

    # SCD Type 2 configuration (Gold layer)
    scd_config: ScdConfig | None = None

    # Gold schema for validation
    gold_schema: Any | None = None  # Any: Pandera DataFrameModel class or instance

    def __post_init__(self) -> None:
        """Convert lists to tuples and validate configuration on creation."""
        freeze_sequences(
            self,
            ("fields", "column_groups", "field_policy", "transform_steps"),
        )
        self._resolve_loading_strategy()
        self._validate_config()

    def _resolve_loading_strategy(self) -> None:
        """Resolve loading_strategy from string to enum if provided."""
        resolved = resolve_loading_strategy(self.loading_strategy)
        object.__setattr__(self, "loading_strategy", resolved)

    def _validate_config(self) -> None:
        """Validate configuration values."""
        validations = [
            (not self.pipeline_name, "pipeline_name cannot be empty"),
            (not self.provider, "provider cannot be empty"),
            (not self.entity_type, "entity_type cannot be empty"),
            (
                self.batch_size <= 0,
                f"batch_size must be positive, got {self.batch_size}",
            ),
            (
                self.checkpoint_interval <= 0,
                f"checkpoint_interval must be positive, got {self.checkpoint_interval}",
            ),
            (not self.table.primary_keys, "primary_keys cannot be empty"),
        ]
        for condition, message in validations:
            if condition:
                raise ValueError(message)

    @property
    def lock_key(self) -> str:
        """Generate lock key for runtime locking."""
        return f"pipeline:{self.pipeline_name}"

    @property
    def effective_silver_table(self) -> str:
        """Silver table name with fallback to provider.entity."""
        return self.table.silver_table or f"{self.provider}.{self.entity_type}"

    @property
    def effective_gold_table(self) -> str:
        """Gold table name with fallback to provider.entity."""
        return self.table.gold_table or f"{self.provider}.{self.entity_type}"
