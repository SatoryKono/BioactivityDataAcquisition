"""Pipeline Identity aggregate root.

This module defines the PipelineIdentity aggregate which represents
the immutable identity and metadata of a data pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.providers import ProviderId
from bioetl.domain.value_objects import EntityName, PipelineId


@dataclass(frozen=True)
class PipelineIdentity:
    """Domain aggregate for pipeline identification.

    Encapsulates all information needed to uniquely identify a pipeline
    and its data domain. This is an immutable value aggregate that serves
    as the identity component of a pipeline configuration.

    Attributes:
        pipeline_id: Unique identifier for the pipeline instance.
        provider: Data provider identifier (e.g., "chembl", "uniprot").
        entity: Type of entity being processed (e.g., "activity", "target").
        primary_key: Tuple of field names forming the primary key for deduplication.

    Invariants:
        - All fields are immutable (frozen dataclass)
        - pipeline_id, provider, and entity are required and non-empty
        - provider must be a valid ProviderId enum value
        - entity must be a valid EntityName (snake_case)
        - primary_key is a tuple (immutable sequence)
    """

    pipeline_id: PipelineId
    provider: ProviderId
    entity: EntityName
    primary_key: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate aggregate invariants."""
        if not isinstance(self.primary_key, tuple):
            # Ensure primary_key is always a tuple (defensive)
            object.__setattr__(self, "primary_key", tuple(self.primary_key))


__all__ = ["PipelineIdentity"]
