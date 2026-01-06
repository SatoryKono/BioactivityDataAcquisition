"""Configuration schema definitions for BioETL infrastructure.

This package contains Pydantic/dataclass schemas for validating
and parsing configuration files for pipelines and data sources.

Components:
    pipeline_config: Pipeline-specific configuration schemas.
    source_config: Data source configuration schemas.
    common_config: Shared configuration types.
    silver: Silver layer schema definitions.
    gold: Gold layer schema definitions.

These schemas ensure type safety and validation when loading
YAML configuration files from configs/pipelines/.
"""
