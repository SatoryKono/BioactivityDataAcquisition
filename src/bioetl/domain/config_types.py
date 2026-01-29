"""TypedDict definitions for YAML configuration structures.

These TypedDicts define the shape of external YAML configuration files.
They are used for type-safe parsing and validation of configuration data
before converting to domain dataclasses.

Implements RULES.md §1 - Domain Layer with pure types.
"""

from __future__ import annotations

from typing import Literal, Required, TypedDict

# =============================================================================
# Gold Filter Configuration TypedDicts
# =============================================================================


class GoldColumnFilterDict(TypedDict):
    """YAML structure for column-based filtering."""

    # Column name is the key, values is a list of allowed values
    # Example: standard_type: [IC50, Ki]
    pass  # This is actually a dict[str, list[str]] pattern


class GoldRangeDict(TypedDict, total=False):
    """YAML structure for numeric range filter."""

    min: float
    max: float
    include_min: bool  # Default: True
    include_max: bool  # Default: True


class GoldFiltersDict(TypedDict, total=False):
    """YAML structure for gold_filters section."""

    columns: dict[str, list[str]]
    ranges: dict[str, GoldRangeDict]
    list_length: dict[str, dict[str, int]]  # column -> {min_length, max_length}
    list_contains: dict[str, dict[str, list[str] | str]]  # column -> {values, mode}
    required_fields: list[str]
    exclude_if_present: list[str]


# =============================================================================
# Sink Configuration TypedDicts
# =============================================================================


class CsvExportDict(TypedDict, total=False):
    """YAML structure for CSV export configuration."""

    enabled: bool
    path: str
    delimiter: str
    header: bool
    encoding: str


class BronzeSinkDict(TypedDict, total=False):
    """YAML structure for Bronze layer sink configuration.

    Note: Bronze format MUST be "jsonl" per RULES.md §2.1 and Medallion Architecture.
    Parquet is not allowed for Bronze layer - only JSONL + zstd compression.
    """

    path: str
    format: Literal["jsonl"]  # RULES.md §2.1: Bronze MUST use JSONL + zstd
    save_json: bool


class SilverSinkDict(TypedDict, total=False):
    """YAML structure for Silver layer sink configuration.

    Note: Silver format MUST be "delta" per RULES.md §2.1 and medallion_validator.py.
    Parquet is not allowed for Silver layer to ensure ACID compliance.
    """

    path: str
    format: Literal["delta"]  # RULES.md §2.1: Silver MUST use Delta Lake
    mode: Literal["merge", "append", "overwrite"]
    primary_key: list[str]
    partition_by: list[str]
    classification: Literal["public", "internal", "restricted"]
    forensic_retention: bool
    csv_export: CsvExportDict


class GoldValidationDict(TypedDict, total=False):
    """YAML structure for Gold layer validation."""

    strict: bool


class GoldSinkDict(TypedDict, total=False):
    """YAML structure for Gold layer sink configuration."""

    enabled: bool
    validation: GoldValidationDict
    path: str
    format: Literal["delta", "parquet"]
    mode: Literal["append", "overwrite", "scd2"]
    csv_export: CsvExportDict


class SinkDict(TypedDict, total=False):
    """YAML structure for complete sink configuration."""

    bronze: BronzeSinkDict
    silver: SilverSinkDict
    gold: GoldSinkDict


# =============================================================================
# Transform Configuration TypedDicts
# =============================================================================


class TransformDict(TypedDict, total=False):
    """YAML structure for transformation configuration."""

    version: str
    steps: list[str]


# =============================================================================
# Column Ordering Configuration TypedDicts
# =============================================================================


class ColumnGroupDict(TypedDict, total=False):
    """YAML structure for column group ordering."""

    name: Required[str]
    fields: list[str]
    pattern: str
    provider_order: list[str]


# =============================================================================
# DQ Configuration TypedDicts (Extended)
# =============================================================================


class DQThresholdsDict(TypedDict, total=False):
    """YAML structure for DQ thresholds section."""

    soft_fail: float  # 0.0-1.0, default 0.05
    hard_fail: float  # 0.0-1.0, default 0.20


class DQReportDict(TypedDict, total=False):
    """YAML structure for DQ report configuration."""

    enabled: bool
    format: Literal["json", "yaml", "csv"]
    include_sample_failures: bool
    sample_size: int
    output_path: str | None


class FieldValidationDict(TypedDict, total=False):
    """YAML structure for field validation rule."""

    field: Required[str]
    type: Required[Literal["required", "range", "pattern", "enum", "custom"]]
    nullable: bool
    min: float
    max: float
    pattern: str
    allowed: list[str]
    validator: str
    error_message: str


class CrossFieldValidationDict(TypedDict, total=False):
    """YAML structure for cross-field validation rule."""

    name: Required[str]
    fields: Required[list[str]]
    condition: Required[
        Literal[
            "all_present",
            "any_present",
            "mutually_exclusive",
            "conditional_required",
            "custom",
        ]
    ]
    trigger_field: str
    required_field: str
    validator: str
    error_message: str


class ConditionalValidationDict(TypedDict, total=False):
    """YAML structure for conditional validation rule."""

    name: Required[str]
    condition_field: Required[str]
    condition_value: Required[str | list[str]]
    condition_operator: Literal["eq", "ne", "in", "not_in"]
    then_validations: list[FieldValidationDict]


class DQRulesDict(TypedDict, total=False):
    """YAML structure for data quality rules in pipeline config.

    Supports two modes:
    1. Inline: direct specification of thresholds/validations
    2. File reference: dq_config_file points to external config

    When dq_config_file is present, other fields serve as overrides.
    """

    # Inline thresholds (legacy, for backward compat)
    soft_fail_threshold: float  # 0.0-1.0
    hard_fail_threshold: float  # 0.0-1.0
    strict_validation: bool

    # Extended inline (optional)
    field_validations: list[FieldValidationDict]
    cross_field_validations: list[CrossFieldValidationDict]
    conditional_validations: list[ConditionalValidationDict]
    invalid_record_policy: Literal["quarantine", "skip", "fail"]
    report: DQReportDict


class DQConfigFileDict(TypedDict, total=False):
    """YAML structure for standalone DQ config file.

    Used in configs/dq/_defaults.yaml, configs/dq/providers/*.yaml,
    and configs/dq/entities/{provider}/*.yaml.
    """

    # Metadata
    version: str
    provider: str
    entity: str

    # Core settings
    thresholds: DQThresholdsDict
    strict_validation: bool
    invalid_record_policy: Literal["quarantine", "skip", "fail"]
    report: DQReportDict

    # Hierarchical validations
    common_field_validations: list[FieldValidationDict]
    provider_field_validations: list[FieldValidationDict]
    entity_field_validations: list[FieldValidationDict]

    common_cross_field_validations: list[CrossFieldValidationDict]
    entity_cross_field_validations: list[CrossFieldValidationDict]

    entity_conditional_validations: list[ConditionalValidationDict]


# =============================================================================
# Circuit Breaker Configuration TypedDict
# =============================================================================


class CircuitBreakerDict(TypedDict, total=False):
    """YAML structure for circuit breaker configuration."""

    failure_threshold: int
    recovery_timeout: int  # seconds


# =============================================================================
# Input Filter Configuration TypedDict
# =============================================================================


class InputFilterDict(TypedDict, total=False):
    """YAML structure for input filter configuration."""

    enabled: bool
    source_path: str
    column_name: str
    filter_field: str
    batch_size: int


# =============================================================================
# Source Configuration TypedDicts
# =============================================================================


class ClientConfigDict(TypedDict, total=False):
    """YAML structure for HTTP client configuration."""

    timeout_sec: float
    max_retries: int


class RateLimitDict(TypedDict, total=False):
    """YAML structure for rate limiting configuration."""

    requests_per_second: int
    burst: int


class ProviderConfigDict(TypedDict, total=False):
    """YAML structure for provider-specific configuration."""

    provider: str
    base_url: str
    client: ClientConfigDict
    max_url_length: int
    batch_size: int
    page_size: int
    api_version: str | None


class SourceConfigDict(TypedDict, total=False):
    """YAML structure for source configuration in source files."""

    type: Literal["api", "file"]
    load_strategy: Literal["full", "incremental"]
    batch_size: int
    provider_config: ProviderConfigDict
    circuit_breaker: CircuitBreakerDict
    rate_limit: RateLimitDict


class SourceFileDict(TypedDict):
    """YAML structure for source configuration file (e.g., configs/sources/chembl.yaml)."""

    source: SourceConfigDict


# =============================================================================
# Pipeline Configuration TypedDict (Main)
# =============================================================================


class PipelineConfigDict(TypedDict, total=False):
    """YAML structure for pipeline configuration file.

    This represents the complete structure of a pipeline YAML file
    (e.g., configs/pipelines/chembl/activity.yaml).
    """

    # Required fields
    pipeline_name: Required[str]
    provider: Required[str]
    entity_type: Required[str]

    # Optional metadata
    version: str
    description: str

    # Table configuration
    primary_keys: list[str]
    silver_table: str
    gold_table: str

    # Source reference
    source_file: str

    # Filtering
    gold_filters: GoldFiltersDict
    input_filter: InputFilterDict

    # Transform
    transform: TransformDict
    column_groups: list[ColumnGroupDict]

    # Sink
    sink: SinkDict

    # Data Quality - TWO options:
    # 1. Reference to external file (recommended)
    dq_config_file: str  # Relative path, e.g., "../../dq/entities/chembl/activity.yaml"
    # 2. Inline rules (legacy, or for overrides)
    dq_rules: DQRulesDict

    # Circuit Breaker
    circuit_breaker: CircuitBreakerDict


# =============================================================================
# Runtime Configuration TypedDict (CLI arguments)
# =============================================================================


class RuntimeArgsDict(TypedDict, total=False):
    """TypedDict for CLI runtime arguments.

    Maps CLI arguments to their expected types.
    """

    run_type: Literal["incremental", "backfill", "rebuild"]
    limit: int
    query: str
    resume: bool
    dry_run: bool
    wait_for_lock: bool
    lock_wait_timeout: int
    heartbeat_interval: int
    vacuum_after_run: bool
    vacuum_retention_days: int
    strict_validation: bool
    strict_gold_validation: bool
    input_csv: str
    filter_column: str
    filter_field: str


__all__ = [
    "BronzeSinkDict",
    "CircuitBreakerDict",
    "ClientConfigDict",
    "ConditionalValidationDict",
    "CrossFieldValidationDict",
    "CsvExportDict",
    "DQConfigFileDict",
    "DQReportDict",
    "DQRulesDict",
    "DQThresholdsDict",
    "FieldValidationDict",
    "GoldColumnFilterDict",
    "GoldFiltersDict",
    "GoldRangeDict",
    "GoldSinkDict",
    "GoldValidationDict",
    "InputFilterDict",
    "PipelineConfigDict",
    "ProviderConfigDict",
    "RateLimitDict",
    "RuntimeArgsDict",
    "SilverSinkDict",
    "SinkDict",
    "SourceConfigDict",
    "SourceFileDict",
    "TransformDict",
]
