"""Domain models package.

Contains Pydantic models for structured data that requires validation.
These models define data contracts for metadata sidecar files.
"""

from __future__ import annotations

from bioetl.domain.medallion import Layer
from bioetl.domain.models.filter import (
    ExtractionParams,
    SourceProfile,
    SourceProfileStatus,
    compute_extraction_params_sha256,
)
from bioetl.domain.models.metadata import (
    BronzeMetadata,
    ColumnMetrics,
    DeltaMetrics,
    DQSummary,
    EnvironmentMetadata,
    FileOutputMetadata,
    GoldMetadata,
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
    "Layer",
    "LineageMetadata",
    "PipelineMetadata",
    "RuntimeMetadata",
    "SCDMetadata",
    "SchemaColumnMetadata",
    "SchemaDrift",
    "SchemaMetadata",
    "SilverMetadata",
    "SourceMetadata",
    "SourceProfile",
    "SourceProfileStatus",
    "compute_extraction_params_sha256",
]
