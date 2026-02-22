"""Schema validation for pipeline configuration.

Implements strict validation for pipeline YAML configurations using Pydantic.
Enforces Medallion Architecture constraints and operational limits.

Consolidation Pattern:
Each Pydantic model has a `to_domain()` method that converts to the corresponding
domain dataclass. This eliminates duplicate conversion logic and provides a clean
boundary between infrastructure (YAML parsing) and domain (business logic).
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.resilience import CircuitBreakerConfig as DomainCircuitBreakerConfig
from bioetl.infrastructure.schemas.base_schemas import (
    BaseFilterColumnSchema,
    BaseGoldColumnFilterConfig,
    BaseGoldFiltersConfig,
    BaseGoldListContainsFilterConfig,
    BaseGoldListLengthFilterConfig,
    BaseGoldRangeFilterConfig,
    BaseInputFilterConfig,
)
from bioetl.infrastructure.schemas.composite_config import ColumnGroupSchema


class FieldValidationConfig(BaseModel):
    """Configuration for a single field validation rule.

    Supports: required, not_null, range, pattern, enum, max_length,
    not_empty_list, custom validation types.
    """

    field: str = Field(description="Field name to validate")
    type: Literal[
        "required",
        "not_null",
        "range",
        "pattern",
        "enum",
        "max_length",
        "not_empty_list",
        "custom",
    ] = Field(description="Validation type")
    nullable: bool = Field(default=True, description="Whether field can be null")
    severity: Literal["error", "warn"] = Field(
        default="error", description="Severity level (error or warn)"
    )
    severity_enricher: Literal["error", "warn"] | None = Field(
        default=None,
        description="Override severity when running as enricher in composite pipeline",
    )
    # Range validation
    min: float | None = Field(default=None, description="Minimum value (range)")
    max: float | None = Field(default=None, description="Maximum value (range)")
    # Pattern validation
    pattern: str | None = Field(default=None, description="Regex pattern")
    # Enum validation
    allowed: list[str] = Field(default_factory=list, description="Allowed values")
    # Max length validation
    max_length: int | None = Field(default=None, description="Maximum string length")
    # Custom validation
    validator: str | None = Field(default=None, description="Custom validator name")
    # Error message
    error_message: str | None = Field(default=None, description="Custom error message")


class CrossFieldValidationConfig(BaseModel):
    """Configuration for cross-field validation rule."""

    name: str = Field(description="Unique validation rule name")
    fields: list[str] = Field(description="Fields involved in validation")
    condition: Literal[
        "all_present",
        "any_present",
        "mutually_exclusive",
        "conditional_required",
        "custom",
    ] = Field(description="Validation condition type")
    severity: Literal["error", "warn"] = Field(
        default="error", description="Severity level (error or warn)"
    )
    trigger_field: str | None = Field(
        default=None, description="Field that triggers conditional requirement"
    )
    required_field: str | None = Field(
        default=None, description="Field required when trigger is present"
    )
    validator: str | None = Field(default=None, description="Custom validator name")
    error_message: str | None = Field(default=None, description="Custom error message")


class ConditionalValidationConfig(BaseModel):
    """Configuration for conditional validation rule."""

    name: str = Field(description="Unique validation rule name")
    condition_field: str = Field(description="Field to check for condition")
    condition_value: str | list[str] = Field(description="Value(s) that trigger")
    condition_operator: Literal["eq", "ne", "in", "not_in"] = Field(
        default="eq", description="Comparison operator"
    )
    then_validations: list[FieldValidationConfig] = Field(
        default_factory=list, description="Validations to apply when condition is true"
    )


class DQReportConfig(BaseModel):
    """Configuration for DQ report generation."""

    enabled: bool = Field(default=True, description="Generate DQ reports")
    format: Literal["json", "yaml", "csv"] = Field(
        default="json", description="Report format"
    )
    include_sample_failures: bool = Field(
        default=True, description="Include sample failed records"
    )
    sample_size: int = Field(
        default=10, ge=1, le=100, description="Number of sample failures"
    )
    output_path: str | None = Field(default=None, description="Custom output path")


class DQConfig(BaseModel):
    """Data Quality configuration.

    Pydantic model for YAML parsing. Use `to_domain()` to convert to domain dataclass.

    Attributes:
        soft_fail_threshold: Error rate threshold for warnings (0.0-1.0).
        hard_fail_threshold: Error rate threshold for failures (0.0-1.0).
        strict_validation: If True, apply stricter validation rules.
            Use with caution as it may reject more records.
        field_validations: Field-level validation rules.
        cross_field_validations: Cross-field validation rules.
        conditional_validations: Conditional validation rules.
        invalid_record_policy: Policy for invalid records (quarantine/skip/fail).
        report: DQ report configuration.
    """

    soft_fail_threshold: float = Field(default=0.05)
    hard_fail_threshold: float = Field(default=0.20)
    strict_validation: bool = Field(
        default=False,
        description="Apply stricter validation rules (feature flag)",
    )
    # Extended DQ configuration
    field_validations: list[FieldValidationConfig] = Field(
        default_factory=list, description="Field-level validation rules"
    )
    cross_field_validations: list[CrossFieldValidationConfig] = Field(
        default_factory=list, description="Cross-field validation rules"
    )
    conditional_validations: list[ConditionalValidationConfig] = Field(
        default_factory=list, description="Conditional validation rules"
    )
    invalid_record_policy: Literal["quarantine", "skip", "fail"] = Field(
        default="quarantine", description="Policy for invalid records"
    )
    report: DQReportConfig = Field(
        default_factory=DQReportConfig, description="DQ report configuration"
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> DQConfig:
        """Validate that thresholds are between 0 and 1."""
        DomainDQConfig.validate_thresholds(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )
        return self

    def to_domain(self) -> DomainDQConfig:
        """Convert to domain DQConfig dataclass.

        Returns:
            DomainDQConfig: Immutable domain configuration.
        """
        from bioetl.domain.config import (
            ConditionalValidation as DomainConditionalValidation,
        )
        from bioetl.domain.config import (
            CrossFieldValidation as DomainCrossFieldValidation,
        )
        from bioetl.domain.config import DQReportConfig as DomainDQReportConfig
        from bioetl.domain.config import FieldValidation as DomainFieldValidation

        # Convert field validations
        field_validations = tuple(
            DomainFieldValidation(
                field=fv.field,
                validation_type=fv.type,
                nullable=fv.nullable,
                severity=fv.severity,
                severity_enricher=fv.severity_enricher,
                min_value=fv.min,
                max_value=fv.max,
                pattern=fv.pattern,
                allowed=tuple(fv.allowed),
                max_length=fv.max_length,
                validator=fv.validator,
                error_message=fv.error_message,
            )
            for fv in self.field_validations
        )

        # Convert cross-field validations
        cross_field_validations = tuple(
            DomainCrossFieldValidation(
                name=cfv.name,
                fields=tuple(cfv.fields),
                condition=cfv.condition,
                severity=cfv.severity,
                trigger_field=cfv.trigger_field,
                required_field=cfv.required_field,
                validator=cfv.validator,
                error_message=cfv.error_message,
            )
            for cfv in self.cross_field_validations
        )

        # Convert conditional validations
        conditional_validations = tuple(
            DomainConditionalValidation(
                name=cv.name,
                condition_field=cv.condition_field,
                condition_value=(
                    tuple(cv.condition_value)
                    if isinstance(cv.condition_value, list)
                    else cv.condition_value
                ),
                condition_operator=cv.condition_operator,
                then_validations=tuple(
                    DomainFieldValidation(
                        field=tv.field,
                        validation_type=tv.type,
                        nullable=tv.nullable,
                        severity=tv.severity,
                        severity_enricher=tv.severity_enricher,
                        min_value=tv.min,
                        max_value=tv.max,
                        pattern=tv.pattern,
                        allowed=tuple(tv.allowed),
                        validator=tv.validator,
                        error_message=tv.error_message,
                    )
                    for tv in cv.then_validations
                ),
            )
            for cv in self.conditional_validations
        )

        # Convert report config
        report_config = DomainDQReportConfig(
            enabled=self.report.enabled,
            format=self.report.format,
            include_sample_failures=self.report.include_sample_failures,
            sample_size=self.report.sample_size,
            output_path=self.report.output_path,
        )

        return DomainDQConfig(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
            strict_validation=self.strict_validation,
            field_validations=field_validations,
            cross_field_validations=cross_field_validations,
            conditional_validations=conditional_validations,
            invalid_record_policy=self.invalid_record_policy,
            report=report_config,
        )


class CircuitBreakerConfig(BaseModel):
    """Circuit Breaker configuration.

    Pydantic model for YAML parsing. Use `to_domain()` to convert to domain dataclass.
    """

    failure_threshold: int = Field(default=5, ge=1)
    recovery_timeout: int = Field(default=300, ge=60)

    def to_domain(self) -> DomainCircuitBreakerConfig:
        """Convert to domain CircuitBreakerConfig dataclass.

        Returns:
            DomainCircuitBreakerConfig: Immutable domain configuration.
        """
        return DomainCircuitBreakerConfig(
            failure_threshold=self.failure_threshold,
            recovery_timeout=self.recovery_timeout,
        )


class CsvExportConfig(BaseModel):
    """Configuration for CSV export."""

    enabled: bool = False
    path: str | None = None
    delimiter: str = ","
    header: bool = True
    encoding: str = "utf-8"


class FilterColumnSchema(BaseFilterColumnSchema):
    """Schema for a single filter column configuration."""


class InputFilterConfig(BaseInputFilterConfig):
    """Configuration for input ID filtering from CSV.

    Inherits to_domain() and validate_column_config from BaseInputFilterConfig.

    Supports both single-column and multi-column filtering modes:
    - Single-column: Use column_name and filter_field directly
    - Multi-column: Use columns list for AND-logic filtering

    Pydantic model for YAML parsing. Use `to_domain()` to convert to domain dataclass.
    """

    # Inherits columns from BaseInputFilterConfig.
    # FilterColumnSchema extends BaseFilterColumnSchema with no additional fields.


class MaintenanceConfig(BaseModel):
    """Configuration for automated maintenance operations.

    Controls automatic VACUUM and other maintenance tasks after pipeline runs.

    Attributes:
        auto_vacuum: Enable automatic VACUUM after successful run.
        vacuum_retention_days: Minimum age of files to remove (days).
    """

    auto_vacuum: bool = Field(
        default=False,
        description="Enable automatic VACUUM after successful pipeline run",
    )
    vacuum_retention_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Minimum age of files to remove during VACUUM (days)",
    )


class ApiConfig(BaseModel):
    """Configuration for API connection details."""

    base_url: str | None = None
    from_db: str | None = Field(
        default=None, description="Source database for ID mapping (e.g., ChEMBL)"
    )
    to_db: str | None = Field(
        default=None, description="Target database for ID mapping (e.g., UniProtKB)"
    )


class RateLimitSourceConfig(BaseModel):
    """Rate limit configuration from source YAML.

    Pydantic model for parsing rate_limit section from configs/sources/*.yaml.
    """

    requests_per_second: float = Field(default=5.0, ge=0.1, le=100.0)
    burst: int = Field(default=10, ge=1, le=200)


class ClientSourceConfig(BaseModel):
    """HTTP client configuration from source YAML."""

    timeout_sec: float = Field(default=30.0, ge=1.0, le=300.0)
    max_retries: int = Field(default=3, ge=0, le=10)


class ProviderSourceConfig(BaseModel):
    """Provider-specific configuration from source YAML.

    Pydantic model for parsing provider_config section from configs/sources/*.yaml.
    """

    provider: str | None = None
    base_url: str | None = None
    client: ClientSourceConfig = Field(default_factory=ClientSourceConfig)
    max_url_length: int = Field(default=2000, ge=500, le=8000)
    batch_size: int = Field(default=100, ge=1, le=5000)
    page_size: int = Field(default=1000, ge=100, le=10000)
    api_version: str | None = None
    default_email: str | None = None


class SourceConfig(BaseModel):
    """Configuration for the data source.

    Parses both pipeline source settings and configs/sources/*.yaml structure.
    The `rate_limit`, `circuit_breaker`, and `provider_config` fields capture
    settings from source configuration files.
    """

    model_config = ConfigDict(extra="ignore")

    # Common fields
    email: str | None = None
    api_key: str | None = None
    fields: list[dict[str, str]] = Field(default_factory=list)
    api: ApiConfig = Field(default_factory=ApiConfig)

    # Source file fields (from configs/sources/*.yaml)
    batch_size: int = Field(default=100, ge=1, le=5000)
    rate_limit: RateLimitSourceConfig = Field(default_factory=RateLimitSourceConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    provider_config: ProviderSourceConfig = Field(default_factory=ProviderSourceConfig)


class SinkDQReportConfig(BaseModel):
    """DQ report configuration for sink layers."""

    enabled: bool = Field(
        default=False,
        description="Enable DQ report generation for this layer",
    )
    output_path: str | None = Field(
        default=None,
        description="Output path for report. None = alongside data files.",
    )
    format: Literal["json", "yaml", "html"] = Field(
        default="json",
        description="Report output format",
    )


class SinkLayerConfig(BaseModel):
    """Configuration for a specific data layer (Bronze, Silver, Gold)."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    path: str | None = None
    format: Literal["jsonl", "delta", "parquet"] = "delta"
    mode: str | None = None
    save_json: bool = False
    save_metadata: bool = Field(
        default=False,
        description="Save _metadata.yaml sidecar file with lineage and QC info",
    )
    csv_export: CsvExportConfig = Field(default_factory=CsvExportConfig)
    # Schema drift handling
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = Field(
        default="error", description="How to handle schema drift"
    )
    # DQ report generation
    dq_report: SinkDQReportConfig = Field(
        default_factory=SinkDQReportConfig,
        description="DQ report generation settings for this layer",
    )
    # Deterministic write order (Gold layer)
    deterministic: bool = Field(
        default=True,
        description="Enable deterministic write order for Gold layer output",
    )
    # Partitioning (Silver layer)
    partition_by: list[str] = Field(
        default_factory=list,
        description="Columns to partition Delta tables by (Silver layer)",
    )
    # SCD Type 2 configuration (Gold layer)
    scd_config: dict[str, str] | None = Field(
        default=None,
        description="SCD Type 2 column mapping (valid_from, valid_to, is_current, version)",
    )
    # Flat structure mode
    flat_structure: bool = Field(
        default=False,
        description="If True, Delta data written directly to path without table_name subdirectory. "
        "CSV, metadata, and DQ reports use {table_name}_* naming pattern.",
    )


class GoldRangeFilterConfig(BaseGoldRangeFilterConfig):
    """Schema for range filters in YAML."""


class GoldListLengthFilterConfig(BaseGoldListLengthFilterConfig):
    """Schema for list length filters in YAML."""


class GoldListContainsFilterConfig(BaseGoldListContainsFilterConfig):
    """Schema for list contains filters in YAML."""


class GoldColumnFilterConfig(BaseGoldColumnFilterConfig):
    """Column filter config with operator support.

    Inherits operator, values fields and validate_operator_values() from base.

    Example YAML:
        columns:
          standard_type:
            operator: in
            values: ["IC50", "Ki"]
          pchembl_value:
            operator: is_not_null
    """


class GoldFiltersConfig(BaseGoldFiltersConfig):
    """Schema for gold_filters in YAML.

    Inherits to_domain() from BaseGoldFiltersConfig.

    Supports two formats for columns:
    - Legacy format: {"column_name": ["value1", "value2"]} (IN operator)
    - New format: {"column_name": {"operator": "in", "values": ["value1", "value2"]}}

    Example YAML (legacy format):
        gold_filters:
          columns:
            standard_type: [IC50, Ki]

    Example YAML (new format):
        gold_filters:
          columns:
            standard_type:
              operator: in
              values: [IC50, Ki]
            pchembl_value:
              operator: is_not_null
    """

    # Inherits columns, ranges, list_lengths, list_contains from BaseGoldFiltersConfig.
    # Child filter types (GoldColumnFilterConfig etc.) extend the base types with no
    # additional fields, so the base field definitions are sufficient.


# Regex for semver validation (allows optional 'v' prefix)
# Matches: 1.0.0, v1.0.0, 1.2.3-beta, 1.2.3+build, etc.
SEMVER_PATTERN = re.compile(
    r"^v?"  # Optional 'v' prefix
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"  # Major.Minor.Patch
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"  # Pre-release
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"  # Build metadata
)


class TransformConfig(BaseModel):
    """Configuration for transform versioning and steps.

    Tracks the version and steps of the transformation applied to data,
    enabling full lineage tracking in Silver/Gold metadata.

    Attributes:
        version: Semver-formatted version string (e.g., "1.0.0", "v2.1.0").
        steps: List of transformation step names applied in order.

    Example YAML:
        transform:
          version: "1.0.0"
          steps:
            - normalize_values
            - add_metadata
            - calculate_content_hash
    """

    version: str | None = Field(
        default=None,
        description="Transform version in semver format (e.g., '1.0.0')",
    )
    steps: list[str] = Field(
        default_factory=list,
        description="List of transformation steps applied",
    )

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str | None) -> str | None:
        """Validate that version follows semver format."""
        if v is None:
            return v
        if not SEMVER_PATTERN.match(v):
            raise ValueError(
                f"Invalid semver format '{v}'. "
                "Expected format: MAJOR.MINOR.PATCH (e.g., '1.0.0', 'v2.1.0')"
            )
        return v


class ContentHashConfig(BaseModel):
    """Configures include/exclude field policy for content hash generation."""

    include: list[str] = Field(
        default_factory=list,
        description="Optional allowlist of fields included in content hash.",
    )
    exclude: list[str] = Field(
        default_factory=list,
        description="Optional denylist of fields excluded from content hash.",
    )


class PipelineYamlConfig(BaseModel):
    """Strict schema for pipeline YAML configuration.

    Pydantic model for YAML parsing.

    DQ Config Resolution:
        The dq_config_file field references an external DQ configuration file
        that is loaded through the DQConfigLoader hierarchy. If both dq_config_file
        and dq_overrides are present, dq_overrides acts as inline overrides on top of
        the file-based configuration.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    pipeline_name: str
    provider: str
    entity_type: str
    version: str = "v1"
    description: str | None = Field(
        default=None, description="Human-readable pipeline description"
    )

    batch_size: int = Field(default=100, ge=1, le=5000)
    filter_batch_size: int | None = Field(
        default=None,
        ge=1,
        le=5000,
        description="Deprecated: use source pagination.id_batch_size instead. "
        "Batch size when input_filter is active. Overrides batch_size.",
    )
    page_size_override: int | None = Field(
        default=None,
        ge=1,
        le=10000,
        description="Override source pagination page_size for this pipeline. "
        "The only pagination parameter a pipeline may set. "
        "Source config defines pagination strategy and defaults.",
    )
    checkpoint_interval: int = Field(default=1000, ge=100)

    # DQ Configuration
    # - dq_config_file: Reference to external DQ config file (hierarchical loading)
    # - dq_overrides: Inline DQ rules (used as overrides if dq_config_file present)
    dq_config_file: str | None = Field(
        default=None,
        description="Path to DQ config file relative to pipeline config. "
        "When set, DQ config is loaded from the hierarchical DQ system. "
        "Example: ../../quality/entities/chembl/activity.yaml",
    )
    dq_overrides: DQConfig = Field(
        default_factory=DQConfig,
    )
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)

    # Filter Configuration (ADR-028)
    # - filter_config_file: Reference to external filter config file (hierarchical)
    # - filter_rules: Inline filter overrides (used as overrides if file present)
    # - input_filter/gold_filters: Legacy inline fields (backward compatibility)
    filter_config_file: str | None = Field(
        default=None,
        description="Path to filter config file relative to pipeline config. "
        "When set, filter config is loaded from the hierarchical filter system. "
        "Example: ../../filters/entities/chembl/activity.yaml",
    )
    filter_rules: dict[str, Any] | None = Field(
        default=None,
        description="Inline filter overrides. Applied on top of filter_config_file. "
        "Format: {input_filter: {...}, gold_filters: {...}}",
    )

    # Column ordering configuration (external file)
    column_groups_file: str | None = Field(
        default=None,
        description="Path to column group config file relative to pipeline config.",
    )
    schema_file: str = Field(
        ...,
        min_length=1,
        description="Required path to schema config file relative to pipeline config. "
        "Example: ../../schemas/chembl/activity.yaml",
    )
    data_schema_file: str | None = Field(
        default=None,
        description="Deprecated alias for schema_file. Kept for backward compatibility.",
    )

    business_primary_keys: list[str] | None = Field(default=None, min_length=1)
    technical_primary_key: str = Field(
        default="entity_id",
        min_length=1,
        description="Technical immutable record key in Silver (defaults to entity_id).",
    )
    primary_keys: list[str] | None = Field(
        default=None,
        description="Deprecated alias for business_primary_keys (kept for migration).",
    )
    silver_table: str = Field(
        default="",
        description="Silver table name. Auto-computed as {provider}_{entity_type} if empty.",
    )
    gold_table: str | None = Field(default=None, min_length=1)
    silver_filters: GoldFiltersConfig = Field(default_factory=GoldFiltersConfig)
    gold_filters: GoldFiltersConfig = Field(default_factory=GoldFiltersConfig)

    sink: dict[str, SinkLayerConfig] = Field(default_factory=dict)
    source: SourceConfig = Field(default_factory=SourceConfig)
    input_filter: InputFilterConfig = Field(default_factory=InputFilterConfig)
    maintenance: MaintenanceConfig = Field(default_factory=MaintenanceConfig)
    transform: TransformConfig = Field(default_factory=TransformConfig)
    column_groups: list[ColumnGroupSchema] = Field(
        default_factory=list,
        description="Optional column ordering groups for Silver/Gold output",
    )

    content_hash: ContentHashConfig = Field(
        default_factory=ContentHashConfig,
        description="Content-hash include/exclude rules loaded from schema config.",
    )

    extraction_params: dict[str, str | int | bool] = Field(
        default_factory=dict,
        description="Server-side API query parameters for Bronze extraction (ADR-028 §3). "
        "Merged from filter config file. Keys are provider-specific query params.",
    )

    # Loading strategy (ADR-031)
    loading_strategy: Literal["full_scan_only"] | None = Field(
        default=None,
        description="Explicit loading strategy for the pipeline. "
        "'full_scan_only': Each run performs full scan, checkpoint resume disabled. "
        "See ADR-031.",
    )

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """Validate batch size limit."""
        if v > 5000:
            raise ValueError("batch_size cannot exceed 5000 records")
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider name format."""
        if not v.islower():
            raise ValueError("provider must be lowercase")
        return v

    @model_validator(mode="after")
    def validate_primary_key_split(self) -> PipelineYamlConfig:
        """Validate explicit separation between business and technical PKs.

        Migration rules:
        - business_primary_keys is canonical.
        - primary_keys is accepted as legacy alias.
        - If both are provided, values MUST match exactly.
        """
        if self.business_primary_keys is None and self.primary_keys is None:
            raise ValueError(
                "business_primary_keys is required (or legacy primary_keys during migration)"
            )

        if self.business_primary_keys is None:
            self.business_primary_keys = self.primary_keys

        if (
            self.primary_keys is not None
            and self.business_primary_keys is not None
            and tuple(self.primary_keys) != tuple(self.business_primary_keys)
        ):
            raise ValueError(
                "primary_keys and business_primary_keys mismatch; "
                "use business_primary_keys as canonical naming"
            )

        if (
            self.business_primary_keys is not None
            and self.technical_primary_key in self.business_primary_keys
            and len(self.business_primary_keys) > 1
        ):
            raise ValueError(
                "technical_primary_key MUST NOT be part of composite business_primary_keys"
            )

        return self

    @model_validator(mode="after")
    def validate_entity_type_canonical(self) -> PipelineYamlConfig:
        """Validate that publication entities use canonical names.

        YAML configs MUST use canonical names (publication*) instead of
        ChEMBL API-level names (document*). This ensures consistency
        across all pipeline configurations.

        See ADR-024 for entity naming unification details.

        Raises:
            ValueError: If document* is used instead of publication*.
        """
        from bioetl.domain.registry.publication import validate_publication_entity_type

        error_msg = validate_publication_entity_type(self.entity_type, self.provider)
        if error_msg:
            raise ValueError(error_msg)
        return self

    @model_validator(mode="after")
    def validate_medallion_formats(self) -> PipelineYamlConfig:
        """Validate Medallion Architecture format constraints.

        RULES.md §2.1:
        - Bronze MUST use JSONL + zstd format (not parquet, not delta)
        - Silver MUST use Delta Lake format (not parquet)
        - Gold MAY use Delta Lake or Parquet

        Note:
            Bronze format is auto-defaulted to 'jsonl' since that's the only
            allowed format per RULES.md. This allows pipeline configs to omit
            the format field for Bronze layer.

        Raises:
            ValueError: If layer format violates Medallion Architecture constraints.
        """
        bronze_config = self.sink.get("bronze")
        silver_config = self.sink.get("silver")

        # Bronze MUST use JSONL only (RULES.md §2.1)
        # Auto-default to jsonl since it's the only allowed format
        if bronze_config:
            # Since SinkLayerConfig defaults to "delta", we auto-correct to "jsonl"
            # This allows pipeline configs to omit format for Bronze
            bronze_config.format = "jsonl"

        # Silver MUST use Delta Lake (RULES.md §2.1)
        # Strict positive check: only "delta" is allowed. This prevents bypass
        # with formats like "jsonl" or "csv" that the previous negative check
        # (format == "parquet") would not catch.
        if silver_config and silver_config.format != "delta":
            raise ValueError(
                f"Silver layer MUST use 'delta' format (RULES.md §2.1). "
                f"Got '{silver_config.format}'. Only Delta Lake is allowed for Silver layer."
            )

        # Gold MAY use delta or parquet (RULES.md §2.1) - no validation needed

        return self
