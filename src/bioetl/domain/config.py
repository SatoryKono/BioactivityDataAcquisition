"""Domain configuration objects.

This module defines configuration value objects used within the Domain and Application layers.
These are distinct from Infrastructure configuration schemas (Pydantic) to maintain
strict layer separation.

Consolidated configuration classes (post-refactoring):
- DQConfig: Data Quality thresholds
- TableConfig: Database tables and keys
- PipelineConfig: Complete immutable pipeline configuration
- RuntimeConfig: CLI/runtime parameters (Value Object)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from bioetl.domain.filter_config import GoldFilterConfig


@dataclass(frozen=True)
class DQConfig:
    """Configuration for Data Quality thresholds.

    Attributes:
        soft_fail_threshold: Error rate threshold for warnings (0.0-1.0).
        hard_fail_threshold: Error rate threshold for failures (0.0-1.0).
        strict_validation: If True, apply stricter validation rules that may
            reject more records. Use with caution in production. Default: False.
    """

    soft_fail_threshold: float = 0.05
    hard_fail_threshold: float = 0.20
    strict_validation: bool = False

    def __post_init__(self) -> None:
        """Validate threshold invariants on creation."""
        self.validate_thresholds(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )

    @staticmethod
    def validate_thresholds(
        *, soft_fail_threshold: float, hard_fail_threshold: float
    ) -> None:
        """Validate ordering and bounds for DQ thresholds."""
        if not 0.0 <= soft_fail_threshold <= 1.0:
            raise ValueError(
                "soft_fail_threshold must be between 0.0 and 1.0 inclusive"
            )
        if not 0.0 <= hard_fail_threshold <= 1.0:
            raise ValueError(
                "hard_fail_threshold must be between 0.0 and 1.0 inclusive"
            )
        if soft_fail_threshold >= hard_fail_threshold:
            raise ValueError(
                "soft_fail_threshold must be strictly less than hard_fail_threshold"
            )


@dataclass(frozen=True)
class TableConfig:
    """Configuration for database tables and keys."""

    primary_keys: list[str] = field(default_factory=lambda: ["entity_id"])
    silver_table: str | None = None
    gold_table: str | None = None
    # Write modes from YAML sink config
    silver_write_mode: Literal["merge", "append", "overwrite"] = "merge"
    gold_write_mode: Literal["append", "overwrite", "scd2"] = "append"
    partition_cols: list[str] = field(default_factory=list)
    # Schema drift handling for Silver layer
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error"


@dataclass(frozen=True)
class PipelineConfig:
    """Immutable pipeline configuration.

    Contains static configuration that doesn't change during execution.
    Frozen dataclass ensures immutability after creation.

    This is the consolidated domain configuration object that combines
    identity, data quality, table, and processing settings.
    """

    # Identity
    pipeline_name: str
    provider: str
    entity_type: str

    # Table configuration
    primary_keys: list[str]
    silver_table: str
    gold_table: str | None = None
    write_mode: Literal["merge", "append", "overwrite"] = "merge"
    gold_write_mode: Literal["append", "overwrite", "scd2"] = "append"
    partition_cols: list[str] = field(default_factory=list)
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error"

    # Processing
    gold_filters: GoldFilterConfig | None = None  # Configurable Gold layer filters
    batch_size: int = 100
    checkpoint_interval: int = 1000
    fields: list[str] = field(default_factory=list)

    # Data Quality
    dq: DQConfig = field(default_factory=DQConfig)

    def __post_init__(self) -> None:
        """Validate configuration on creation."""
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
            (not self.primary_keys, "primary_keys cannot be empty"),
        ]
        for condition, message in validations:
            if condition:
                raise ValueError(message)

    @property
    def lock_key(self) -> str:
        """Generate lock key for distributed locking."""
        return f"pipeline:{self.pipeline_name}"

    @property
    def table(self) -> TableConfig:
        """Get TableConfig for backward compatibility."""
        return TableConfig(
            primary_keys=self.primary_keys,
            silver_table=self.silver_table,
            gold_table=self.gold_table,
            silver_write_mode=self.write_mode,
            gold_write_mode=self.gold_write_mode,
            partition_cols=self.partition_cols,
            on_schema_mismatch=self.on_schema_mismatch,
        )


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime execution parameters.

    Contains parameters that may vary between pipeline runs
    but are fixed during a single execution. These are typically
    passed via CLI arguments.

    This is a Value Object that belongs in the domain layer because
    it has no I/O dependencies and represents immutable runtime state.
    """

    run_type: RunType
    resume: bool = False
    limit: int | None = None
    heartbeat_interval: int = 30
    wait_for_lock: bool = False
    lock_wait_timeout: int = 300
    lock_ttl: int | None = None
    query: str | None = None
    dry_run: bool = False

    # VACUUM automation (Phase 1 refactoring)
    # When enabled, VACUUM is executed after successful pipeline run
    vacuum_after_run: bool = False
    vacuum_retention_days: int = 7

    def __post_init__(self) -> None:
        """Validate runtime config."""
        if self.limit is not None and self.limit <= 0:
            raise ValueError(f"limit must be positive or None, got {self.limit}")
        if self.heartbeat_interval <= 0:
            raise ValueError(
                f"heartbeat_interval must be positive, got {self.heartbeat_interval}"
            )
        if self.lock_wait_timeout <= 0:
            raise ValueError(
                f"lock_wait_timeout must be positive, got {self.lock_wait_timeout}"
            )
        if self.vacuum_retention_days <= 0:
            raise ValueError(
                f"vacuum_retention_days must be positive, got {self.vacuum_retention_days}"
            )

    @property
    def effective_lock_ttl(self) -> int:
        """Derived TTL for lock renewal based on runtime config."""
        return self.lock_ttl or self.heartbeat_interval * 3
