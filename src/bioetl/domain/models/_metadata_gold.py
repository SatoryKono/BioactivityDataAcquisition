# mypy: disable-error-code="misc"
"""Gold layer metadata models.

Contains schema contract, SCD tracking, composite extensions,
and the complete GoldMetadata aggregate for sidecar files.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.medallion import Layer
from bioetl.domain.models._metadata_common import (
    BaseOutputMetadata,
    EnvironmentMetadata,
    GovernanceMetadata,
    PipelineMetadata,
    RuntimeMetadata,
)
from bioetl.domain.models._metadata_silver import DQSummary, LineageMetadata

__all__ = [
    "CompositeOutputExt",
    "CompositeSchemaValidationMetadata",
    "GoldMetadata",
    "GoldOutputExt",
    "SCDMetadata",
    "SchemaColumnMetadata",
    "SchemaMetadata",
]


class GoldOutputExt(BaseModel):
    """Gold-specific output metadata extension.

    Tracks partitioning and format for consumption layer.

    Attributes:
        partition_count: Number of partitions.
        format: Output format (delta or parquet).
    """

    partition_count: int = Field(
        default=0,
        ge=0,
        description="Number of partitions",
    )
    format: Literal["delta", "parquet"] = Field(
        default="delta",
        description="Output format",
    )


class CompositeSchemaValidationMetadata(BaseModel):
    """Schema validation metadata for composite Gold outputs.

    Captures whether strict schema validation was applied before writing
    composite merged data and records the outcome in sidecar metadata.
    """

    enabled: bool = Field(
        default=False,
        description="Whether schema validation was enabled",
    )
    strict: bool | None = Field(
        default=None,
        description="Whether strict schema validation was required",
    )
    status: Literal["passed", "not_run"] = Field(
        default="not_run",
        description="Schema validation outcome for this write",
    )


class CompositeOutputExt(GoldOutputExt):
    """Composite-specific extension for Gold output metadata.

    Formalizes lineage fields that are also emitted in composite records
    (`_composite_*`, `_source_providers`, `_enrichment_*`, `_lineage_*`) and
    adds schema validation sidecar metadata for merged outputs.
    """

    composite_run_id: str | None = Field(
        default=None,
        description="Composite run identifier from _composite_run_id",
    )
    source_providers: list[str] = Field(
        default_factory=list,
        description="Source providers from _source_providers",
    )
    enrichment_status: dict[str, str] = Field(
        default_factory=dict,
        description="Per-enricher status map from _enrichment_status",
    )
    lineage_created_at: datetime | None = Field(
        default=None,
        description="Lineage timestamp from _lineage_created_at",
    )
    schema_validation: CompositeSchemaValidationMetadata = Field(
        default_factory=CompositeSchemaValidationMetadata,
        description="Schema validation details for composite merged write",
    )


class SchemaColumnMetadata(BaseModel):
    """Schema column definition.

    Attributes:
        name: Column name.
        type: Column data type.
        nullable: Whether column allows nulls.
    """

    name: str = Field(description="Column name")
    type: str = Field(description="Data type")
    nullable: bool = Field(default=True, description="Nullable")


class SchemaMetadata(BaseModel):
    """Schema contract metadata for Gold layer.

    Attributes:
        contract_path: Path to schema contract file.
        version: Schema version.
        validation: Validation mode (strict for Gold).
        columns: Column definitions.
    """

    contract_path: str | None = Field(
        default=None, description="Path to schema contract file"
    )
    version: str = Field(default="1.0", description="Schema version")
    validation: Literal["strict", "lenient"] = Field(
        default="strict", description="Validation mode"
    )
    columns: list[SchemaColumnMetadata] = Field(
        default_factory=list, description="Column definitions"
    )


class SCDMetadata(BaseModel):
    """SCD Type 2 tracking metadata.

    Attributes:
        enabled: Whether SCD2 is enabled.
        effective_date_column: Column for effective date.
        end_date_column: Column for end date.
        current_flag_column: Column for current flag.
        new_versions_created: Number of new versions created.
        records_expired: Number of records expired.
    """

    enabled: bool = Field(default=False, description="SCD2 enabled")
    effective_date_column: str = Field(
        default="_valid_from", description="Effective date column"
    )
    end_date_column: str = Field(default="_valid_to", description="End date column")
    current_flag_column: str = Field(
        default="_is_current", description="Current flag column"
    )
    new_versions_created: int = Field(default=0, description="New versions created")
    records_expired: int = Field(default=0, description="Records expired")


class GoldMetadata(BaseModel):
    """Complete metadata for Gold layer sidecar file.

    Includes schema contract, SCD tracking, and governance metadata.

    ADR-029: Uses unified BaseOutputMetadata + GoldOutputExt composition.
    """

    model_config = ConfigDict(populate_by_name=True)

    version: str = Field(default="1.1", description="Metadata schema version")
    layer: Layer = Field(default=Layer.GOLD, description="Medallion layer")
    runtime: RuntimeMetadata = Field(description="Runtime context")
    pipeline: PipelineMetadata = Field(description="Pipeline identification")
    lineage: LineageMetadata = Field(
        default_factory=LineageMetadata, description="Lineage information"
    )
    schema_info: SchemaMetadata = Field(
        default_factory=SchemaMetadata,
        description="Schema contract",
        alias="schema",
    )
    dq_summary: DQSummary = Field(
        default_factory=DQSummary, description="Data quality summary"
    )
    output: BaseOutputMetadata = Field(
        default_factory=BaseOutputMetadata, description="Base output metrics"
    )
    output_ext: GoldOutputExt | CompositeOutputExt = Field(
        default_factory=GoldOutputExt,
        description="Gold-specific or composite-specific output metrics",
    )
    scd: SCDMetadata | None = Field(default=None, description="SCD Type 2 metadata")
    environment: EnvironmentMetadata = Field(description="Environment information")
    # Cross-reference to DQ report
    dq_report_path: str | None = Field(
        default=None,
        description="Path to corresponding DQ report file (if generated)",
    )
    governance: GovernanceMetadata | None = Field(
        default=None, description="Governance metadata for data stewardship"
    )
