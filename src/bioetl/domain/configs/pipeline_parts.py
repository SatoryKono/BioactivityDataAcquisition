"""Pipeline configuration parts for composition.

This module provides decomposed configuration value objects that can be
composed into a full PipelineConfiguration. This enables better separation
of concerns and more flexible configuration management.

The design follows the Builder pattern where individual configuration
aspects can be modified independently before assembly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HashingConfiguration:
    """Configuration for hashing behavior.

    Defines how business keys are hashed for row identification
    and deduplication purposes.

    Attributes:
        business_key_columns: Tuple of column names that form the business key.
        hash_algorithm: Hash algorithm to use (default: sha256).
        include_nulls: Whether to include null values in hash computation.
    """

    business_key_columns: tuple[str, ...] = ()
    hash_algorithm: str = "sha256"
    include_nulls: bool = False


@dataclass(frozen=True)
class IndexConfiguration:
    """Configuration for index management.

    Defines primary and secondary indexes for output data.

    Attributes:
        primary_index: Column name for primary index (if any).
        secondary_indexes: Tuple of column names for secondary indexes.
    """

    primary_index: str | None = None
    secondary_indexes: tuple[str, ...] = ()


@dataclass(frozen=True)
class MetadataConfiguration:
    """Configuration for metadata handling.

    Defines what metadata columns should be added to output data.

    Attributes:
        include_source_timestamp: Add extraction timestamp column.
        include_source_index: Add source row index column.
        include_database_version: Add database version column.
        custom_fields: Additional custom metadata fields.
    """

    include_source_timestamp: bool = True
    include_source_index: bool = True
    include_database_version: bool = True
    custom_fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ErrorHandlingConfiguration:
    """Configuration for error handling behavior.

    Defines how the pipeline handles errors during execution.

    Attributes:
        fail_fast: Stop immediately on first error.
        max_retries: Maximum retry attempts for transient errors.
        retry_delay_seconds: Base delay between retries.
        log_errors: Whether to log errors to structured logging.
    """

    fail_fast: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    log_errors: bool = True


@dataclass(frozen=True)
class PipelinePartsConfiguration:
    """Aggregated pipeline configuration from component parts.

    This class composes individual configuration aspects into a single
    configuration object. It provides a cleaner interface compared to
    passing many individual parameters.

    Example:
        >>> config = PipelinePartsConfiguration(
        ...     hashing=HashingConfiguration(
        ...         business_key_columns=("molecule_chembl_id",),
        ...     ),
        ...     indexing=IndexConfiguration(
        ...         primary_index="activity_id",
        ...     ),
        ... )
        >>> print(config.hashing.business_key_columns)
        ('molecule_chembl_id',)
    """

    hashing: HashingConfiguration = field(default_factory=HashingConfiguration)
    indexing: IndexConfiguration = field(default_factory=IndexConfiguration)
    metadata: MetadataConfiguration = field(default_factory=MetadataConfiguration)
    error_handling: ErrorHandlingConfiguration = field(
        default_factory=ErrorHandlingConfiguration
    )

    @classmethod
    def from_pipeline_config(cls, config: Any) -> "PipelinePartsConfiguration":
        """Create from existing PipelineConfig.

        This factory method extracts relevant configuration from a
        PipelineConfig instance for use with the new decomposed structure.

        Args:
            config: PipelineConfig instance.

        Returns:
            PipelinePartsConfiguration extracted from the input config.
        """
        # Extract hashing config
        hashing_section = getattr(config, "hashing", None)
        if hashing_section is None:
            hashing_section = getattr(getattr(config, "quality", None), "hashing", None)

        business_keys: tuple[str, ...] = ()
        if hashing_section is not None:
            fields = getattr(hashing_section, "business_key_fields", None)
            if fields is not None:
                business_keys = tuple(fields)

        hashing = HashingConfiguration(business_key_columns=business_keys)

        # Use defaults for other configurations for now
        return cls(hashing=hashing)


__all__ = [
    "ErrorHandlingConfiguration",
    "HashingConfiguration",
    "IndexConfiguration",
    "MetadataConfiguration",
    "PipelinePartsConfiguration",
]
