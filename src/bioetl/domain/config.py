"""Domain configuration objects.

This module defines configuration value objects used within the Domain and Application layers.
These are distinct from Infrastructure configuration schemas (Pydantic) to maintain
strict layer separation.

Consolidated configuration classes (post-refactoring):
- ValidationConfig: Centralized validation ranges for domain value objects
- DQConfig: Data Quality thresholds
- TableConfig: Database tables and keys
- PipelineConfig: Complete immutable pipeline configuration
- RuntimeConfig: CLI/runtime parameters (Value Object)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from bioetl.domain.composite.config import ColumnGroupConfig
from bioetl.domain.medallion import GoldWriteMode, LoadingStrategy, SilverWriteMode
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig


# =============================================================================
# Validation Configuration
# =============================================================================


@dataclass(frozen=True, slots=True)
class ValidationConfig:
    """Centralized configuration for validation ranges.

    Provides configurable validation parameters for domain value objects
    and validation functions. This enables:
    - Consistent validation across all components
    - Override capability via pipeline config
    - Single source of truth for validation rules

    Attributes:
        min_publication_year: Minimum valid publication year. Default 1800
            covers modern scientific publications. Use 1500 for historical
            databases like Semantic Scholar.
        max_publication_year: Maximum valid publication year. Default 2100.
        min_molecular_weight: Minimum molecular weight in Daltons. Default 10.0.
        max_molecular_weight: Maximum molecular weight in Daltons. Default 10000.0
            covers small molecules to large peptides.
        max_pmid: Maximum valid PubMed ID. Default 10_000_000_000.
        max_taxonomy_id: Maximum valid NCBI Taxonomy ID. Default 10_000_000.
        min_pchembl_value: Minimum pChEMBL value. Default 0.0.
        max_pchembl_value: Maximum pChEMBL value. Default 15.0 (-log10(10^-15 M)).
        molecular_weight_precision: Decimal precision for MW rounding. Default 10.

    Example:
        >>> config = ValidationConfig()
        >>> config.min_publication_year
        1800
        >>> # Override for Semantic Scholar (older publications)
        >>> ss_config = ValidationConfig(min_publication_year=1500)
        >>> ss_config.min_publication_year
        1500

    """

    # Publication year range
    min_publication_year: int = 1800
    max_publication_year: int = 2100

    # Molecular properties
    min_molecular_weight: float = 10.0
    max_molecular_weight: float = 10_000.0
    molecular_weight_precision: int = 10

    # Identifiers
    max_pmid: int = 10_000_000_000
    max_taxonomy_id: int = 10_000_000

    # Activity values
    min_pchembl_value: float = 0.0
    max_pchembl_value: float = 15.0

    def __post_init__(self) -> None:
        """Validate configuration invariants."""
        self._validate_ranges()

    def _validate_ranges(self) -> None:
        """Validate that min/max ranges are valid."""
        validations = [
            (
                self.min_publication_year >= self.max_publication_year,
                "min_publication_year must be less than max_publication_year",
            ),
            (
                self.min_molecular_weight >= self.max_molecular_weight,
                "min_molecular_weight must be less than max_molecular_weight",
            ),
            (
                self.min_pchembl_value >= self.max_pchembl_value,
                "min_pchembl_value must be less than max_pchembl_value",
            ),
            (
                self.molecular_weight_precision < 0,
                "molecular_weight_precision must be non-negative",
            ),
        ]
        for condition, message in validations:
            if condition:
                raise ValueError(message)


# Default singleton instance for use when no custom config is provided
DEFAULT_VALIDATION_CONFIG = ValidationConfig()


@dataclass(frozen=True, slots=True)
class FieldValidation:
    """Configuration for a single field validation rule.

    Supports multiple validation types:
    - required: Field must be present and non-null
    - range: Numeric range validation (min/max)
    - pattern: Regex pattern matching
    - enum: Allowed values validation
    - custom: Custom validator function reference

    Attributes:
        field: Field name to validate.
        validation_type: Type of validation (required, range, pattern, enum, custom).
        nullable: Whether field can be null/None. Default: True.
        min_value: Minimum value for range validation.
        max_value: Maximum value for range validation.
        pattern: Regex pattern for pattern validation.
        allowed: Allowed values for enum validation.
        validator: Validator function name for custom validation.
        error_message: Custom error message template.
    """

    field: str
    validation_type: Literal["required", "range", "pattern", "enum", "custom"]
    nullable: bool = True
    # Range validation
    min_value: float | None = None
    max_value: float | None = None
    # Pattern validation
    pattern: str | None = None
    # Enum validation
    allowed: tuple[str, ...] = ()
    # Custom validation
    validator: str | None = None
    # Custom error message
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.allowed, list):
            object.__setattr__(self, "allowed", tuple(self.allowed))


@dataclass(frozen=True, slots=True)
class CrossFieldValidation:
    """Configuration for cross-field validation rule.

    Validates relationships between multiple fields.

    Attributes:
        name: Unique name for the validation rule.
        fields: Fields involved in the validation.
        condition: Validation condition type.
        error_message: Custom error message template.
    """

    name: str
    fields: tuple[str, ...]
    condition: Literal[
        "all_present",  # All fields must be non-null
        "any_present",  # At least one field must be non-null
        "mutually_exclusive",  # Only one field can be non-null
        "conditional_required",  # If field A present, field B required
        "custom",  # Custom validation function
    ]
    # For conditional_required: (trigger_field, required_field)
    trigger_field: str | None = None
    required_field: str | None = None
    # Custom validation
    validator: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.fields, list):
            object.__setattr__(self, "fields", tuple(self.fields))


@dataclass(frozen=True, slots=True)
class ConditionalValidation:
    """Configuration for conditional validation rule.

    Applies validation only when a condition is met.

    Attributes:
        name: Unique name for the validation rule.
        condition_field: Field to check for condition.
        condition_value: Value that triggers the validation.
        condition_operator: Comparison operator (eq, ne, in, not_in).
        then_validations: Field validations to apply when condition is true.
    """

    name: str
    condition_field: str
    condition_value: str | tuple[str, ...]
    condition_operator: Literal["eq", "ne", "in", "not_in"] = "eq"
    then_validations: tuple[FieldValidation, ...] = ()

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.condition_value, list):
            object.__setattr__(self, "condition_value", tuple(self.condition_value))
        if isinstance(self.then_validations, list):
            object.__setattr__(self, "then_validations", tuple(self.then_validations))


@dataclass(frozen=True, slots=True)
class DQReportConfig:
    """Configuration for DQ report generation.

    Attributes:
        enabled: Whether to generate DQ reports. Default: True.
        format: Report format (json, yaml, csv). Default: json.
        include_sample_failures: Include sample failed records. Default: True.
        sample_size: Number of sample failures to include. Default: 10.
        output_path: Path for report output. None = use pipeline output dir.
    """

    enabled: bool = True
    format: Literal["json", "yaml", "csv"] = "json"
    include_sample_failures: bool = True
    sample_size: int = 10
    output_path: str | None = None


@dataclass(frozen=True, slots=True)
class DQConfig:
    """Configuration for Data Quality thresholds and validations.

    Attributes:
        soft_fail_threshold: Error rate threshold for warnings (0.0-1.0).
        hard_fail_threshold: Error rate threshold for failures (0.0-1.0).
        strict_validation: If True, apply stricter validation rules that may
            reject more records. Use with caution in production. Default: False.
        field_validations: Field-level validation rules.
        cross_field_validations: Cross-field validation rules.
        conditional_validations: Conditional validation rules.
        invalid_record_policy: Policy for handling invalid records.
        report: DQ report configuration.
    """

    soft_fail_threshold: float = 0.05
    hard_fail_threshold: float = 0.20
    strict_validation: bool = False
    # Extended DQ configuration
    field_validations: tuple[FieldValidation, ...] = ()
    cross_field_validations: tuple[CrossFieldValidation, ...] = ()
    conditional_validations: tuple[ConditionalValidation, ...] = ()
    invalid_record_policy: Literal["quarantine", "skip", "fail"] = "quarantine"
    report: DQReportConfig = field(default_factory=DQReportConfig)

    def __post_init__(self) -> None:
        """Validate threshold invariants on creation."""
        self.validate_thresholds(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )
        self._ensure_immutability()

    def _ensure_immutability(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.field_validations, list):
            object.__setattr__(self, "field_validations", tuple(self.field_validations))
        if isinstance(self.cross_field_validations, list):
            object.__setattr__(
                self, "cross_field_validations", tuple(self.cross_field_validations)
            )
        if isinstance(self.conditional_validations, list):
            object.__setattr__(
                self, "conditional_validations", tuple(self.conditional_validations)
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


def _resolve_loading_strategy(
    loading_strategy: LoadingStrategy | str | None,
    force_full_scan: bool,
) -> LoadingStrategy:
    """Resolve loading_strategy from explicit value or force_full_scan flag.

    Priority:
    1. Explicit loading_strategy if provided
    2. Derived from force_full_scan for backward compatibility

    Args:
        loading_strategy: Explicit strategy value or None
        force_full_scan: Legacy boolean flag

    Returns:
        Resolved LoadingStrategy enum value
    """
    if loading_strategy is not None:
        if isinstance(loading_strategy, LoadingStrategy):
            return loading_strategy
        return LoadingStrategy.from_string(loading_strategy)
    # Derive from force_full_scan for backward compatibility
    return LoadingStrategy.from_force_full_scan(force_full_scan)


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
    column_groups: tuple[ColumnGroupConfig, ...] = ()

    # Data Quality
    dq: DQConfig = field(default_factory=DQConfig)

    # Transform versioning (lineage tracking)
    transform_version: str | None = None
    transform_steps: tuple[str, ...] = ()

    # Pagination strategy (ADR-030, ADR-031)
    # When True, checkpoint-based resume is disabled and each run performs a full scan.
    # Deduplication is handled on Silver layer via content_hash.
    # Required for publication entities due to API offset instability.
    force_full_scan: bool = False

    # Loading strategy (ADR-031)
    # Explicit formalization of data loading approach.
    # - FULL_SCAN_ONLY: Each run performs full scan, checkpoint resume disabled
    # - WATERMARK_BASED: Incremental loading via watermark (placeholder, not implemented)
    # If not specified, derived from force_full_scan for backward compatibility.
    loading_strategy: LoadingStrategy | str | None = None

    def __post_init__(self) -> None:
        """Convert lists to tuples and validate configuration on creation."""
        self._ensure_immutability()
        self._convert_write_modes()
        self._resolve_loading_strategy()
        self._validate_config()

    def _ensure_immutability(self) -> None:
        """Convert incoming lists to tuples for immutability."""
        for attr in ("primary_keys", "partition_cols", "fields", "column_groups", "transform_steps"):
            val = getattr(self, attr)
            if isinstance(val, list):
                object.__setattr__(self, attr, tuple(val))

    def _convert_write_modes(self) -> None:
        """Convert string write modes to enums (backward compatibility)."""
        object.__setattr__(
            self, "write_mode", _convert_silver_write_mode(self.write_mode)
        )
        object.__setattr__(
            self, "gold_write_mode", _convert_gold_write_mode(self.gold_write_mode)
        )

    def _resolve_loading_strategy(self) -> None:
        """Resolve loading_strategy from explicit value or force_full_scan.

        Ensures consistency between loading_strategy and force_full_scan fields.
        Validates that explicit loading_strategy matches force_full_scan when both set.
        """
        resolved = _resolve_loading_strategy(
            self.loading_strategy, self.force_full_scan
        )
        object.__setattr__(self, "loading_strategy", resolved)

        # Validate consistency: if both explicit and force_full_scan conflict
        if (
            self.loading_strategy == LoadingStrategy.FULL_SCAN_ONLY
            and not self.force_full_scan
        ):
            # Update force_full_scan to match explicit loading_strategy
            object.__setattr__(self, "force_full_scan", True)

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
    heartbeat_interval: int = 30
    wait_for_lock: bool = False
    lock_wait_timeout: int = 300
    lock_ttl: int | None = 90
    query: str | None = None
    dry_run: bool = False

    # VACUUM automation (Phase 1 refactoring)
    # When enabled, VACUUM is executed after successful pipeline run
    vacuum_after_run: bool = False
    vacuum_retention_days: int = 7

    # Storage optimization (Unifies cleanup policies)
    # Controls explicit storage maintenance (vacuum, old file removal)
    optimize_storage: bool = False

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


# =============================================================================
# Memory Monitoring Configuration
# =============================================================================


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    """Configuration for memory-aware batch processing.

    Used by MemoryMonitor (infrastructure layer) to configure adaptive
    batch sizing based on memory pressure detection.

    Attributes:
        max_batch_memory_mb: Maximum memory per batch in MB (default: 512MB).
        memory_pressure_threshold: Threshold (0.0-1.0) for reducing batch size (default: 0.8).
        min_batch_size: Minimum batch size even under memory pressure (default: 10).
        check_interval_records: Check memory every N records (default: 100).
        enable_adaptive_sizing: Enable/disable adaptive batch sizing (default: True).

    Example:
        >>> config = MemoryConfig()
        >>> config.memory_pressure_threshold
        0.8
        >>> config.max_batch_memory_mb
        512
    """

    max_batch_memory_mb: int = 512
    memory_pressure_threshold: float = 0.8
    min_batch_size: int = 10
    check_interval_records: int = 100
    enable_adaptive_sizing: bool = True
