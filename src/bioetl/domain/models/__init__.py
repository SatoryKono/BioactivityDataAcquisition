"""Domain models package.

Contains Pydantic models for structured data that requires validation.
These models define data contracts for metadata sidecar files.
"""

from bioetl.domain.models.filter import ExtractionParams
from bioetl.domain.models.metadata import (
    BronzeMetadata,
    ColumnMetrics,
    DeltaMetrics,
    DQSummary,
    EnvironmentMetadata,
    FileOutputMetadata,
    GoldMetadata,
    LayerType,
    LineageMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    SCDMetadata,
    SchemaColumnMetadata,
    SchemaDrift,
    SchemaMetadata,
    SilverMetadata,
    SourceMetadata,
)

__all__ = [
    "BronzeMetadata",
    "ColumnMetrics",
    "DQSummary",
    "DeltaMetrics",
    "EnvironmentMetadata",
    "ExtractionParams",
    "FileOutputMetadata",
    "GoldMetadata",
    "LayerType",
    "LineageMetadata",
    "PipelineMetadata",
    "RuntimeMetadata",
    "SCDMetadata",
    "SchemaColumnMetadata",
    "SchemaDrift",
    "SchemaMetadata",
    "SilverMetadata",
    "SourceMetadata",
]
