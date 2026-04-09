"""Metadata models for Medallion layer sidecar files.

Defines Pydantic models for _metadata.yaml files that accompany
data artifacts in Bronze, Silver, and Gold layers.

Implements RULES.md 2.3 and 02-user-rules.md 2.4:
- Lineage tracking
- QC information
- Runtime context

ADR-029: Output metadata unification across Medallion layers.

Version: 1.1

Re-export facade: actual definitions live in sub-modules
(_metadata_common, _metadata_bronze, _metadata_silver, _metadata_gold).
"""

from __future__ import annotations

from bioetl.domain.models._metadata_bronze import (
    APIRequestDetails,
    BronzeMetadata,
    BronzeOutputExt,
    FileOutputMetadata,
    InputSnapshotRef,
    RateLimitInfo,
    SourceMetadata,
)
from bioetl.domain.models._metadata_common import (
    BaseOutputMetadata,
    EnvironmentMetadata,
    GovernanceLineageConfig,
    GovernanceMetadata,
    PipelineMetadata,
    QualityExpectations,
    RuntimeMetadata,
    RunTypeEnum,
)
from bioetl.domain.models._metadata_gold import (
    CompositeOutputExt,
    CompositeSchemaValidationMetadata,
    GoldMetadata,
    GoldOutputExt,
    SCDMetadata,
    SchemaColumnMetadata,
    SchemaMetadata,
)
from bioetl.domain.models._metadata_silver import (
    ColumnMetrics,
    DeltaMetrics,
    DQSummary,
    LineageMetadata,
    SchemaDrift,
    SilverMetadata,
    SilverOutputExt,
)

__all__ = [
    "APIRequestDetails",
    "BaseOutputMetadata",
    "BronzeMetadata",
    "BronzeOutputExt",
    "ColumnMetrics",
    "CompositeOutputExt",
    "CompositeSchemaValidationMetadata",
    "DQSummary",
    "DeltaMetrics",
    "EnvironmentMetadata",
    "FileOutputMetadata",
    "GoldMetadata",
    "GoldOutputExt",
    "GovernanceLineageConfig",
    "GovernanceMetadata",
    "InputSnapshotRef",
    "LineageMetadata",
    "PipelineMetadata",
    "QualityExpectations",
    "RateLimitInfo",
    "RunTypeEnum",
    "RuntimeMetadata",
    "SCDMetadata",
    "SchemaColumnMetadata",
    "SchemaDrift",
    "SchemaMetadata",
    "SilverMetadata",
    "SilverOutputExt",
    "SourceMetadata",
]
