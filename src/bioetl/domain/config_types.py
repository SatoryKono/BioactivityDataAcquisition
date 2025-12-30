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
    """YAML structure for Bronze layer sink configuration."""

    path: str
    format: Literal["jsonl", "parquet"]
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
# DQ Rules Configuration TypedDict
# =============================================================================


class DQRulesDict(TypedDict, total=False):
    """YAML structure for data quality rules."""

    soft_fail_threshold: float  # 0.0-1.0
    hard_fail_threshold: float  # 0.0-1.0
    strict_validation: bool


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

    # Sink
    sink: SinkDict

    # Data Quality
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
    "CsvExportDict",
    "DQRulesDict",
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
