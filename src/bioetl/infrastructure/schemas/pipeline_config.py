# mypy: disable-error-code="misc,untyped-decorator"
"""Schema validation facade for pipeline configuration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from bioetl.domain.composite import DataSchemaConfig
from bioetl.domain.constants import DEFAULT_CHECKPOINT_INTERVAL
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.schemas.composite_config import ColumnGroupSchema
from bioetl.infrastructure.schemas.pipeline_config_common import (
    CircuitBreakerYamlConfig,
)
from bioetl.infrastructure.schemas.pipeline_config_common_schemas import (
    AuthoritativeContentHashPolicyConfig,
    ContentHashConfig,
    FilterColumnSchema,
    GoldColumnFilterConfig,
    GoldFiltersConfig,
    GoldListContainsFilterConfig,
    GoldListLengthFilterConfig,
    GoldRangeFilterConfig,
    InputFilterYamlConfig,
    MaintenanceConfig,
    SilverFiltersConfig,
    SinkDQReportConfig,
    SinkLayerConfig,
    SourceProfileYamlConfig,
    TransformConfig,
)
from bioetl.infrastructure.schemas.pipeline_config_dq import (
    ConditionalValidationConfig,
    CrossFieldValidationConfig,
    DQReportYamlConfig,
    DQYamlConfig,
    FieldValidationConfig,
)
from bioetl.infrastructure.schemas.pipeline_config_provider import (
    ApiConfig,
    ClientSourceConfig,
    ProviderSourceConfig,
    RateLimitSourceConfig,
    SourceConfig,
)

__all__ = [
    "ApiConfig",
    "AuthoritativeContentHashPolicyConfig",
    "CircuitBreakerYamlConfig",
    "ClientSourceConfig",
    "ConditionalValidationConfig",
    "ContentHashConfig",
    "CrossFieldValidationConfig",
    "DQReportYamlConfig",
    "DQYamlConfig",
    "FieldPolicyConfigSchema",
    "FieldValidationConfig",
    "FilterColumnSchema",
    "GoldColumnFilterConfig",
    "GoldFiltersConfig",
    "GoldListContainsFilterConfig",
    "GoldListLengthFilterConfig",
    "GoldRangeFilterConfig",
    "InputFilterYamlConfig",
    "MaintenanceConfig",
    "PipelineYamlConfig",
    "ProviderSourceConfig",
    "RateLimitSourceConfig",
    "SilverFiltersConfig",
    "SinkDQReportConfig",
    "SinkLayerConfig",
    "SourceConfig",
    "SourceProfileYamlConfig",
    "TransformConfig",
]


def _serialize_schema_value(value: object) -> object:
    """Convert immutable domain containers to Pydantic-safe plain containers."""
    if isinstance(value, Mapping):
        return {str(key): _serialize_schema_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_serialize_schema_value(item) for item in value]
    return value


class FieldPolicyConfigSchema(BaseModel):
    """Explicit field-level pipeline policy overrides."""

    model_config = ConfigDict(extra="forbid")

    optional: bool | None = Field(
        default=None,
        description=(
            "Explicit optionality override for this field. "
            "When omitted, runtime falls back to derived effective_optional_v1."
        ),
    )
    empty_as_missing: bool | None = Field(
        default=None,
        description=(
            "Override structural missing-value semantics for this field. "
            "When true, empty containers may be treated as missing. "
            "When false, blank strings are preserved instead of being treated as missing."
        ),
    )
    coercion_policy: Literal["default", "no_string_coercion"] | None = Field(
        default=None,
        description=(
            "Override structural coercion behavior for non-string fields. "
            "'no_string_coercion' disables string-to-number/string-to-bool coercion."
        ),
    )
    boolean_true_values: list[str] = Field(
        default_factory=list,
        description=(
            "Optional normalized truthy tokens for boolean coercion overrides. "
            "Applied case-insensitively after trim."
        ),
    )
    boolean_false_values: list[str] = Field(
        default_factory=list,
        description=(
            "Optional normalized falsy tokens for boolean coercion overrides. "
            "Applied case-insensitively after trim."
        ),
    )

    @model_validator(mode="after")
    def validate_boolean_vocabularies(self) -> FieldPolicyConfigSchema:
        """Reject overlapping boolean vocabularies after normalization."""
        true_values = {
            value.strip().lower() for value in self.boolean_true_values if value.strip()
        }
        false_values = {
            value.strip().lower()
            for value in self.boolean_false_values
            if value.strip()
        }
        overlap = true_values & false_values
        if overlap:
            overlap_values = ", ".join(sorted(overlap))
            raise ValueError(
                "field_policy boolean vocabularies must not overlap; "
                f"got: {overlap_values}"
            )
        return self


class PipelineYamlConfig(BaseModel):
    """Strict schema for pipeline YAML configuration."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    pipeline_name: str
    provider: str
    entity_type: str
    version: str = "v1"
    description: str | None = Field(
        default=None, description="Human-readable pipeline description"
    )
    batch_size: int = Field(default=100, ge=1, le=5000)
    page_size_override: int | None = Field(
        default=None,
        ge=1,
        le=10000,
        description="Override source pagination page_size for this pipeline. "
        "The only pagination parameter a pipeline may set. "
        "Source config defines pagination strategy and defaults.",
    )
    checkpoint_interval: int = Field(default=DEFAULT_CHECKPOINT_INTERVAL, ge=100)
    dq_config_file: str | None = Field(
        default=None,
        description="Path to DQ config file relative to pipeline config. "
        "When set, DQ config is loaded from the hierarchical DQ system. "
        "Example: ../../entities/chembl/activity.yaml",
    )
    dq_overrides: DQYamlConfig = Field(default_factory=DQYamlConfig)
    circuit_breaker: CircuitBreakerYamlConfig = Field(
        default_factory=CircuitBreakerYamlConfig
    )
    filter_config_file: str | None = Field(
        default=None,
        description="Path to filter config file relative to pipeline config. "
        "When set, filter config is loaded from the hierarchical filter system. "
        "Example: ../../entities/chembl/activity.yaml",
    )
    filter_rules: JsonDict | None = Field(
        default=None,
        description="Inline filter overrides. Applied on top of filter_config_file. "
        "Format: {input_filter: {...}, gold_filters: {...}}",
    )
    business_primary_keys: list[str] | None = Field(default=None, min_length=1)
    technical_primary_key: str = Field(
        default="entity_id",
        min_length=1,
        description="Technical immutable record key in Silver (defaults to entity_id).",
    )
    silver_table: str = Field(
        default="",
        description="Silver table name. Auto-computed as {provider}.{entity_type} if empty.",
    )
    gold_table: str | None = Field(default=None, min_length=1)
    silver_filters: SilverFiltersConfig = Field(default_factory=SilverFiltersConfig)
    gold_filters: GoldFiltersConfig = Field(default_factory=GoldFiltersConfig)

    def _customize_sink_schema(schema: dict[str, Any]) -> None:
        """Customize JSON Schema for layer-aware sink constraints."""
        # Grab the reference to the SinkLayerConfig child schema
        child_ref = schema.get("additionalProperties", {})
        schema["additionalProperties"] = False

        schema["properties"] = {
            "bronze": {
                "allOf": [child_ref],
                "properties": {
                    "mode": {"type": ["string", "null"], "enum": ["append", None]},
                },
            },
            "silver": {
                "allOf": [child_ref],
                "properties": {
                    "mode": {"type": ["string", "null"], "enum": ["append", "merge", None]},
                },
            },
            "gold": {
                "allOf": [child_ref],
                "properties": {
                    "mode": {"type": ["string", "null"], "enum": ["append", "overwrite", "scd2", None]},
                },
            },
        }

    sink: dict[str, SinkLayerConfig] = Field(
        default_factory=dict,
        json_schema_extra=_customize_sink_schema,
    )
    source: SourceConfig = Field(default_factory=SourceConfig)
    input_filter: InputFilterYamlConfig = Field(default_factory=InputFilterYamlConfig)
    maintenance: MaintenanceConfig = Field(default_factory=MaintenanceConfig)
    transform: TransformConfig = Field(default_factory=TransformConfig)
    field_policy: dict[str, FieldPolicyConfigSchema] = Field(
        default_factory=dict,
        description=(
            "Explicit field-level policy overrides for runtime structural policy. "
            "Use this to set optional semantics directly instead of relying on "
            "derived effective_optional_v1."
        ),
    )
    data_schema: DataSchemaConfig | None = Field(
        default=None,
        description=(
            "Full Medallion layer projection config projected from unified schema. "
            "Used by writers to enforce include_groups/exclude_fields at runtime."
        ),
    )

    @field_serializer("data_schema")
    def serialize_data_schema(
        self,
        value: DataSchemaConfig | None,
    ) -> object:
        """Serialize frozen nested projection mappings as plain JSON objects."""
        if value is None:
            return None
        return _serialize_schema_value(asdict(value))

    column_groups: list[ColumnGroupSchema] = Field(
        default_factory=list,
        description="Optional column ordering groups for Silver/Gold output",
    )
    content_hash: ContentHashConfig = Field(
        default_factory=ContentHashConfig,
        description="Content-hash include/exclude rules loaded from schema config.",
    )
    content_hash_policy: AuthoritativeContentHashPolicyConfig | None = Field(
        default=None,
        description=(
            "Single runtime-authoritative content-hash policy loaded from the "
            "entity root hash_policy section."
        ),
    )
    extraction_params: dict[str, str | int | bool] = Field(
        default_factory=dict,
        description="Server-side API query parameters for Bronze extraction (ADR-028 §3). "
        "Merged from filter config file. Keys are provider-specific query params.",
    )
    source_profile: SourceProfileYamlConfig = Field(
        default_factory=SourceProfileYamlConfig,
        description=(
            "Versioned source-side extraction policy metadata. "
            "It fingerprints extraction_params separately from Silver filtering."
        ),
    )
    loading_strategy: Literal["full_scan_only"] | None = Field(
        default=None,
        description="Explicit loading strategy for the pipeline. "
        "'full_scan_only': Each run performs full scan, checkpoint resume disabled. "
        "See ADR-031.",
    )

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, value: int) -> int:
        """Validate batch size limit."""
        if value > 5000:
            raise ValueError("batch_size cannot exceed 5000 records")
        return value

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        """Validate provider name format."""
        if not value.islower():
            raise ValueError("provider must be lowercase")
        return value

    @model_validator(mode="before")
    @classmethod
    def reject_semantic_silver_filters(cls, data: object) -> object:
        """Reject semantic Silver rules before strict field validation."""
        if not isinstance(data, dict):
            return data
        from bioetl.domain.filtering.silver_config import (
            validate_no_semantic_silver_filter_payload,
        )

        return validate_no_semantic_silver_filter_payload(data)

    def _validate_primary_key_presence(self) -> None:
        """Ensure business primary keys are specified."""
        if self.business_primary_keys is None:
            raise ValueError("business_primary_keys is required")

    def _validate_technical_key_separation(self) -> None:
        """Ensure technical PK is not in composite business PKs."""
        if (
            self.business_primary_keys is not None
            and self.technical_primary_key in self.business_primary_keys
            and len(self.business_primary_keys) > 1
        ):
            raise ValueError(
                "technical_primary_key MUST NOT be part of composite business_primary_keys"
            )

    def _validate_sink_sort_by(self) -> None:
        """Ensure enabled sink layers have sort_by configured."""
        for layer_name in ("silver", "gold"):
            layer = self.sink.get(layer_name)
            if layer is None or not layer.enabled:
                continue
            if not layer.sort_by:
                raise ValueError(
                    f"sink.{layer_name}.sort_by must be configured for deterministic output"
                )

    @model_validator(mode="after")
    def validate_sink_modes(self) -> PipelineYamlConfig:
        """Validate layer-aware sink modes and keys."""
        valid_layers = {"bronze", "silver", "gold"}
        valid_modes = {
            "bronze": {"append"},
            "silver": {"append", "merge"},
            "gold": {"append", "overwrite", "scd2"},
        }

        for layer_name, layer_config in self.sink.items():
            if layer_name not in valid_layers:
                raise ValueError(f"Unknown sink layer: '{layer_name}'. Allowed: bronze, silver, gold.")

            mode = layer_config.mode
            if mode is not None:
                if mode not in valid_modes[layer_name]:
                    valid_str = ", ".join(sorted(valid_modes[layer_name]))
                    raise ValueError(f"Invalid mode '{mode}' for {layer_name} layer. Allowed: {valid_str}.")

        return self

    @model_validator(mode="after")
    def validate_primary_key_split(self) -> PipelineYamlConfig:
        """Validate explicit separation between business and technical PKs."""
        self._validate_primary_key_presence()
        self._validate_technical_key_separation()
        self._validate_sink_sort_by()
        self.source_profile.assert_matches_extraction_params(self.extraction_params)
        return self

    @model_validator(mode="after")
    def validate_entity_type_canonical(self) -> PipelineYamlConfig:
        """Validate that publication entities use canonical names."""
        from bioetl.domain.registry.publication import (
            get_publication_entity_type_validation_error,
        )

        error_msg = get_publication_entity_type_validation_error(
            self.entity_type, self.provider
        )
        if error_msg:
            raise ValueError(error_msg)
        return self

    @model_validator(mode="after")
    def validate_medallion_formats(self) -> PipelineYamlConfig:
        """Validate Medallion Architecture format constraints."""
        bronze_config = self.sink.get("bronze")
        silver_config = self.sink.get("silver")
        gold_config = self.sink.get("gold")

        if bronze_config:
            bronze_config.format = "jsonl"

        if silver_config and silver_config.format != "delta":
            raise ValueError(
                f"Silver layer MUST use 'delta' format (RULES.md §2.1). "
                f"Got '{silver_config.format}'. Only Delta Lake is allowed for Silver layer."
            )

        if gold_config and gold_config.format != "delta":
            raise ValueError(
                f"Gold layer MUST use 'delta' format (RULES.md §2.1). "
                f"Got '{gold_config.format}'. Only Delta Lake is allowed for Gold layer."
            )
        return self
