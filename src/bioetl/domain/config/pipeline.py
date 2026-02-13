"""Pipeline configuration object.

Defines the immutable PipelineConfig value object — the main domain
configuration for a single ETL pipeline run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.composite.config import ColumnGroupConfig
from bioetl.domain.config._converters import freeze_sequences, resolve_loading_strategy
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.config.table import TableConfig
from bioetl.domain.medallion import GoldWriteMode, LoadingStrategy, SilverWriteMode

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Immutable pipeline configuration.

    Contains static configuration that doesn't change during execution.
    Frozen dataclass ensures immutability after creation.

    This is the consolidated domain configuration object that combines
    identity, data quality, table, and processing settings.

    Table-related fields (primary_keys, silver_table, gold_table,
    write modes, partition_cols, on_schema_mismatch) are stored in the
    nested ``table`` field (:class:`TableConfig`).  Convenience
    properties forward the most common accesses so that
    ``config.primary_keys`` continues to work alongside the canonical
    ``config.table.primary_keys`` form.
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
    batch_size: int = 100
    checkpoint_interval: int = 1000
    fields: tuple[str, ...] = ()
    column_groups: tuple[ColumnGroupConfig, ...] = ()

    # Data Quality
    dq: DQConfig = field(default_factory=DQConfig)

    # Transform versioning (lineage tracking)
    transform_version: str | None = None
    transform_steps: tuple[str, ...] = ()

    # Loading strategy (ADR-031)
    # - FULL_SCAN_ONLY: Each run performs full scan, checkpoint resume disabled
    # - None: Default incremental behavior with checkpoint resume
    loading_strategy: LoadingStrategy | str | None = None

    def __post_init__(self) -> None:
        """Convert lists to tuples and validate configuration on creation."""
        freeze_sequences(
            self,
            ("fields", "column_groups", "transform_steps"),
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
        """Generate lock key for distributed locking."""
        return f"pipeline:{self.pipeline_name}"

    # ------------------------------------------------------------------
    # Convenience forwarding properties for backward compatibility.
    # Canonical access is via ``self.table.<field>``.
    # ------------------------------------------------------------------

    @property
    def primary_keys(self) -> tuple[str, ...]:
        """Shortcut for ``self.table.primary_keys``."""
        return self.table.primary_keys

    @property
    def silver_table(self) -> str | None:
        """Shortcut for ``self.table.silver_table``."""
        return self.table.silver_table

    @property
    def gold_table(self) -> str | None:
        """Shortcut for ``self.table.gold_table``."""
        return self.table.gold_table

    @property
    def write_mode(self) -> SilverWriteMode:
        """Shortcut for ``self.table.silver_write_mode``."""
        return self.table.silver_write_mode

    @property
    def gold_write_mode(self) -> GoldWriteMode:
        """Shortcut for ``self.table.gold_write_mode``."""
        return self.table.gold_write_mode

    @property
    def partition_cols(self) -> tuple[str, ...]:
        """Shortcut for ``self.table.partition_cols``."""
        return self.table.partition_cols

    @property
    def on_schema_mismatch(self) -> str:
        """Shortcut for ``self.table.on_schema_mismatch``."""
        return self.table.on_schema_mismatch
