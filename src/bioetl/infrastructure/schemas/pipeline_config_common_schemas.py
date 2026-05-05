# mypy: disable-error-code="misc,untyped-decorator"
"""Common non-provider schemas extracted from pipeline_config."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from bioetl.domain.types import ScdConfig as DomainScdConfig
from bioetl.infrastructure.schemas.base_schemas import (
    BaseFilterColumnSchema,
    BaseGoldColumnFilterConfig,
    BaseGoldFiltersConfig,
    BaseGoldListContainsFilterConfig,
    BaseGoldListLengthFilterConfig,
    BaseGoldRangeFilterConfig,
    BaseInputFilterConfig,
)
from bioetl.infrastructure.schemas.pipeline_config_common import CsvExportConfig

__all__ = [
    "SEMVER_PATTERN",
    "ContentHashConfig",
    "FilterColumnSchema",
    "GoldColumnFilterConfig",
    "GoldFiltersConfig",
    "GoldListContainsFilterConfig",
    "GoldListLengthFilterConfig",
    "GoldRangeFilterConfig",
    "InputFilterYamlConfig",
    "MaintenanceConfig",
    "ScdConfigYamlConfig",
    "SinkDQReportConfig",
    "SinkLayerConfig",
    "TransformConfig",
]


class FilterColumnSchema(BaseFilterColumnSchema):
    """Schema for a single filter column configuration."""


class InputFilterYamlConfig(BaseInputFilterConfig):
    """Configuration for input ID filtering from CSV."""


class MaintenanceConfig(BaseModel):
    """Configuration for automated maintenance operations."""

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


class ScdConfigYamlConfig(BaseModel):
    """Pydantic boundary schema for Gold SCD2 configuration."""

    model_config = ConfigDict(extra="forbid")

    business_key: str | list[str] | None = Field(
        default=None,
        description="Business key column or columns used for SCD2 identity.",
    )
    scd_type: int = Field(
        default=2,
        validation_alias=AliasChoices("type", "scd_type"),
        description="SCD type. Only value 2 is supported.",
    )
    valid_from_col: str = Field(
        default="valid_from",
        validation_alias=AliasChoices("valid_from_col", "valid_from"),
        description="Column storing SCD validity start timestamp.",
    )
    valid_to_col: str = Field(
        default="valid_to",
        validation_alias=AliasChoices("valid_to_col", "valid_to"),
        description="Column storing SCD validity end timestamp.",
    )
    current_flag_col: str = Field(
        default="is_current",
        validation_alias=AliasChoices("current_flag_col", "is_current"),
        description="Column storing current-row flag.",
    )
    version_col: str = Field(
        default="version",
        validation_alias=AliasChoices("version_col", "version"),
        description="Column storing SCD version number.",
    )

    def to_domain(
        self,
        *,
        primary_keys: tuple[str, ...] | list[str] | None = None,
    ) -> DomainScdConfig:
        """Convert validated YAML config to typed domain config."""
        return DomainScdConfig.from_mapping(
            self.model_dump(mode="python"),
            primary_keys=primary_keys,
        )


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
    idempotency_contract: (
        Literal[
            "merge_upsert",
            "scd2",
            "overwrite_rebuild",
            "append_log",
            "partition_append_with_stable_partition_key",
            "occurrence_only",
            "disallowed",
        ]
        | None
    ) = Field(
        default=None,
        description="Explicit idempotency classification for sink write-mode governance.",
    )
    save_json: bool = False
    save_metadata: bool = Field(
        default=False,
        description="Save _metadata.yaml sidecar file with lineage and QC info",
    )
    csv_export: CsvExportConfig = Field(default_factory=CsvExportConfig)
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = Field(
        default="error", description="How to handle schema drift"
    )
    dq_report: SinkDQReportConfig = Field(
        default_factory=SinkDQReportConfig,
        description="DQ report generation settings for this layer",
    )
    deterministic: bool = Field(
        default=True,
        description="Enable deterministic write order for Gold layer output",
    )
    sort_by: list[str] = Field(
        default_factory=list,
        description="Deterministic sort policy for layer output ordering.",
    )
    partition_by: list[str] = Field(
        default_factory=list,
        description="Columns to partition Delta tables by (Silver layer)",
    )
    scd_config: ScdConfigYamlConfig | None = Field(
        default=None,
        description="SCD Type 2 column mapping (valid_from, valid_to, is_current, version)",
    )
    flat_structure: bool = Field(
        default=False,
        description="If True, Delta data written directly to path without table_name subdirectory. "
        "CSV, metadata, and DQ reports use {table_name}_* naming pattern.",
    )

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, value: list[str]) -> list[str]:
        """Validate deterministic sort policy column names."""
        normalized = [column.strip() for column in value]
        if any(not column for column in normalized):
            raise ValueError("sort_by must not contain empty column names")
        if len(normalized) != len(set(normalized)):
            raise ValueError("sort_by must not contain duplicate columns")
        return normalized


class GoldRangeFilterConfig(BaseGoldRangeFilterConfig):
    """Schema for range filters in YAML."""


class GoldListLengthFilterConfig(BaseGoldListLengthFilterConfig):
    """Schema for list length filters in YAML."""


class GoldListContainsFilterConfig(BaseGoldListContainsFilterConfig):
    """Schema for list contains filters in YAML."""


class GoldColumnFilterConfig(BaseGoldColumnFilterConfig):
    """Column filter config with operator support."""


class GoldFiltersConfig(BaseGoldFiltersConfig):
    """Schema for gold_filters in YAML."""


SEMVER_PATTERN = re.compile(
    r"^v?"
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


class TransformConfig(BaseModel):
    """Configuration for transform versioning and steps."""

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
    def validate_semver(cls, value: str | None) -> str | None:
        """Validate that version follows semver format."""
        if value is None:
            return value
        if not SEMVER_PATTERN.match(value):
            raise ValueError(
                f"Invalid semver format '{value}'. "
                "Expected format: MAJOR.MINOR.PATCH (e.g., '1.0.0', 'v2.1.0')"
            )
        return value


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
