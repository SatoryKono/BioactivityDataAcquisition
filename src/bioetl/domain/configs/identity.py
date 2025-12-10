"""Pipeline identity configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, PlainValidator

if TYPE_CHECKING:
    from bioetl.domain.aggregates.pipeline_identity import PipelineIdentity
    from bioetl.domain.providers import ProviderId
    from bioetl.domain.value_objects import EntityName, PipelineId


def _coerce_pipeline_id(value: Any) -> "PipelineId":
    """Coerce str to PipelineId for backwards compatibility."""
    from bioetl.domain.value_objects import PipelineId

    if isinstance(value, PipelineId):
        return value
    if isinstance(value, str):
        return PipelineId(value)
    raise TypeError(f"Expected str or PipelineId, got {type(value).__name__}")


def _coerce_provider_id(value: Any) -> "ProviderId":
    """Coerce str to ProviderId for backwards compatibility."""
    from bioetl.domain.providers import ProviderId

    if isinstance(value, ProviderId):
        return value
    if isinstance(value, str):
        return ProviderId(value)
    raise TypeError(f"Expected str or ProviderId, got {type(value).__name__}")


def _coerce_entity_name(value: Any) -> "EntityName":
    """Coerce str to EntityName for backwards compatibility."""
    from bioetl.domain.value_objects import EntityName

    if isinstance(value, EntityName):
        return value
    if isinstance(value, str):
        return EntityName(value)
    raise TypeError(f"Expected str or EntityName, got {type(value).__name__}")


def _coerce_primary_key(value: str | list[str] | None) -> list[str]:
    """Coerce primary_key to list if string is provided."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return list(value)


# Annotated types with validators and serializers for Pydantic
PipelineIdField = Annotated[
    Any,
    PlainValidator(_coerce_pipeline_id),
    PlainSerializer(lambda v: str(v), return_type=str),
]

ProviderIdField = Annotated[
    Any,
    PlainValidator(_coerce_provider_id),
    PlainSerializer(lambda v: v.value if hasattr(v, "value") else str(v), return_type=str),
]

EntityNameField = Annotated[
    Any,
    PlainValidator(_coerce_entity_name),
    PlainSerializer(lambda v: str(v), return_type=str),
]


class PipelineIdentityConfig(BaseModel):
    """Pipeline identification and metadata.

    Groups fields that identify the pipeline and its data domain.
    This is a frozen immutable model for thread-safety and hashability.

    Uses Value Objects for type-safe fields with automatic
    validation and serialization. Accepts both str and Value Objects
    for backwards compatibility.

    Attributes:
        pipeline_id: Unique identifier for the pipeline (PipelineId).
        provider: Data provider identifier (ProviderId enum).
        entity: Type of entity being extracted (EntityName).
        primary_key: List of fields that form the primary key for deduplication.
    """

    pipeline_id: PipelineIdField = Field(
        ..., description="Unique identifier for the pipeline"
    )
    provider: ProviderIdField = Field(..., description="Data provider identifier")
    entity: EntityNameField = Field(..., description="Entity type being extracted")
    primary_key: Annotated[list[str], PlainValidator(_coerce_primary_key)] = Field(
        default_factory=list, description="Primary key fields for deduplication"
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    def to_domain(self) -> "PipelineIdentity":
        """Convert to domain value object aggregate.

        Returns:
            PipelineIdentity: Rich domain model with Value Objects.

        Example:
            >>> config = PipelineIdentityConfig(
            ...     pipeline_id="chembl.activity",
            ...     provider="chembl",
            ...     entity="activity",
            ...     primary_key=["activity_id"]
            ... )
            >>> identity = config.to_domain()
            >>> isinstance(identity.pipeline_id, PipelineId)
            True
        """
        # Lazy import to avoid circular dependency
        from bioetl.domain.aggregates.pipeline_identity import PipelineIdentity

        return PipelineIdentity(
            pipeline_id=self.pipeline_id,
            provider=self.provider,
            entity=self.entity,
            primary_key=tuple(self.primary_key),
        )


__all__ = ["PipelineIdentityConfig"]
