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

from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig


@dataclass(frozen=True, slots=True)
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


def _convert_silver_write_mode(mode: SilverWriteMode | str) -> SilverWriteMode:
    """Convert string to SilverWriteMode."""
    if isinstance(mode, SilverWriteMode):
        return mode
    return SilverWriteMode.from_string(mode)


def _convert_gold_write_mode(mode: GoldWriteMode | str) -> GoldWriteMode:
    """Convert string to GoldWriteMode."""
    if isinstance(mode, GoldWriteMode):
        return mode
    return GoldWriteMode.from_string(mode)


@dataclass(frozen=True, slots=True)
class TableConfig:
    """Configuration for database tables and keys.

    All collection fields are immutable tuples to ensure true immutability
    of the frozen dataclass. The __post_init__ converts any incoming lists
    to tuples for backward compatibility.

    Write modes are now typed using domain enums (SilverWriteMode, GoldWriteMode)
    instead of Literal strings for type safety and policy enforcement.
    """

    primary_keys: tuple[str, ...] = ("entity_id",)
    silver_table: str | None = None
    gold_table: str | None = None
    # Write modes using domain enums (R1 refactoring)
    silver_write_mode: SilverWriteMode | str = SilverWriteMode.MERGE
    gold_write_mode: GoldWriteMode | str = GoldWriteMode.APPEND
    partition_cols: tuple[str, ...] = ()
    # Schema drift handling for Silver layer
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error"

    def __post_init__(self) -> None:
        """Convert incoming values to proper types for immutability."""
        # Use object.__setattr__ because frozen=True
        if isinstance(self.primary_keys, list):
            object.__setattr__(self, "primary_keys", tuple(self.primary_keys))
        if isinstance(self.partition_cols, list):
            object.__setattr__(self, "partition_cols", tuple(self.partition_cols))
        # Convert string write modes to enums (backward compatibility)
        object.__setattr__(
            self,
            "silver_write_mode",
            _convert_silver_write_mode(self.silver_write_mode),
        )
        object.__setattr__(
            self, "gold_write_mode", _convert_gold_write_mode(self.gold_write_mode)
        )


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Immutable pipeline configuration.

    Contains static configuration that doesn't change during execution.
    Frozen dataclass ensures immutability after creation.

    This is the consolidated domain configuration object that combines
    identity, data quality, table, and processing settings.

    Write modes use domain enums (SilverWriteMode, GoldWriteMode) for type
    safety. String values are accepted for backward compatibility and
    converted to enums in __post_init__.
    """

    # Identity
    pipeline_name: str
    provider: str
    entity_type: str

    # Table configuration
    primary_keys: tuple[str, ...]
    silver_table: str
    gold_table: str | None = None
    # Write modes using domain enums (R1 refactoring)
    write_mode: SilverWriteMode | str = SilverWriteMode.MERGE
    gold_write_mode: GoldWriteMode | str = GoldWriteMode.APPEND
    partition_cols: tuple[str, ...] = ()
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error"

    # Processing
    gold_filters: GoldFilterConfig | None = None  # Configurable Gold layer filters
    batch_size: int = 100
    checkpoint_interval: int = 1000
    fields: tuple[str, ...] = ()

    # Data Quality
    dq: DQConfig = field(default_factory=DQConfig)

    def __post_init__(self) -> None:
        """Convert lists to tuples and validate configuration on creation."""
        self._ensure_immutability()
        self._convert_write_modes()
        self._validate_config()

    def _ensure_immutability(self) -> None:
        """Convert incoming lists to tuples for immutability."""
        if isinstance(self.primary_keys, list):
            object.__setattr__(self, "primary_keys", tuple(self.primary_keys))
        if isinstance(self.partition_cols, list):
            object.__setattr__(self, "partition_cols", tuple(self.partition_cols))
        if isinstance(self.fields, list):
            object.__setattr__(self, "fields", tuple(self.fields))

    def _convert_write_modes(self) -> None:
        """Convert string write modes to enums (backward compatibility)."""
        object.__setattr__(
            self, "write_mode", _convert_silver_write_mode(self.write_mode)
        )
        object.__setattr__(
            self, "gold_write_mode", _convert_gold_write_mode(self.gold_write_mode)
        )

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


@dataclass(frozen=True, slots=True)
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
    heartbeat_interval: int = 20
    wait_for_lock: bool = False
    lock_wait_timeout: int = 300
    lock_ttl: int | None = 60
    query: str | None = None
    dry_run: bool = False

    # VACUUM automation (Phase 1 refactoring)
    # When enabled, VACUUM is executed after successful pipeline run
    vacuum_after_run: bool = False
    vacuum_retention_days: int = 7

    # Medallion invariants validation (REQ-CONF-001)
    # When True, Medallion config violations fail the pipeline
    # When False, violations are logged as warnings
    strict_validation: bool = False

    # Gold layer schema validation (strict mode)
    # When True, pipelines fail if Gold schema is not provided
    # When False (default), missing Gold schema skips validation
    # Use False during migration, True for production readiness
    strict_gold_validation: bool = False

    def __post_init__(self) -> None:
        """Validate runtime config."""
        self._validate_positive_values()

    def _validate_positive_values(self) -> None:
        """Validate that numeric fields have positive values."""
        validations = [
            (
                self.limit is not None and self.limit <= 0,
                f"limit must be positive or None, got {self.limit}",
            ),
            (
                self.heartbeat_interval <= 0,
                f"heartbeat_interval must be positive, got {self.heartbeat_interval}",
            ),
            (
                self.lock_wait_timeout <= 0,
                f"lock_wait_timeout must be positive, got {self.lock_wait_timeout}",
            ),
            (
                self.vacuum_retention_days <= 0,
                f"vacuum_retention_days must be positive, got {self.vacuum_retention_days}",
            ),
        ]
        for condition, message in validations:
            if condition:
                raise ValueError(message)

    @property
    def effective_lock_ttl(self) -> int:
        """Derived TTL for lock renewal based on runtime config."""
        return self.lock_ttl or self.heartbeat_interval * 3
