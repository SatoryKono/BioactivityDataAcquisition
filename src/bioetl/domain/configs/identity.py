"""Pipeline identity configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from bioetl.domain.aggregates.pipeline_identity import PipelineIdentity


class PipelineIdentityConfig(BaseModel):
    """Pipeline identification and metadata.

    Groups fields that identify the pipeline and its data domain.
    This is a frozen immutable model for thread-safety and hashability.

    This is a Pydantic config model that uses primitive types (str)
    for serialization compatibility. Use to_domain() to convert to
    the rich domain model with Value Objects.

    Attributes:
        pipeline_id: Unique identifier for the pipeline run.
        provider: Name of the data provider (e.g., "chembl", "uniprot").
        entity: Type of entity being extracted (e.g., "activity", "target").
        primary_key: List of fields that form the primary key for deduplication.
    """

    pipeline_id: str = Field(..., description="Unique identifier for the pipeline")
    provider: str = Field(..., description="Data provider name")
    entity: str = Field(..., description="Entity type being extracted")
    primary_key: list[str] = Field(
        default_factory=list, description="Primary key fields for deduplication"
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("pipeline_id")
    @classmethod
    def validate_pipeline_id_not_empty(cls, value: str) -> str:
        """Ensure pipeline_id is not empty and validate via PipelineId."""
        # Lazy import to avoid circular dependency
        from bioetl.domain.value_objects import PipelineId

        # Validation through value object (will raise if invalid)
        PipelineId(value)
        return value.strip()

    @field_validator("provider")
    @classmethod
    def validate_provider_known(cls, value: str) -> str:
        """Ensure provider identifier is known to the registry.

        Uses lazy import to avoid circular dependencies with providers module.
        """
        # Lazy import to avoid circular dependency
        from bioetl.domain.providers import ProviderId

        known = {provider.value for provider in ProviderId}
        if value not in known:
            raise ValueError(f"Unknown provider: {value}. Known: {known}")
        return value

    @field_validator("entity")
    @classmethod
    def validate_entity_format(cls, value: str) -> str:
        """Ensure entity follows EntityName format (snake_case).

        Uses lazy import to avoid circular dependencies.
        """
        # Lazy import to avoid circular dependency
        from bioetl.domain.value_objects import EntityName

        # Validation through value object (will raise if invalid)
        EntityName(value)
        return value.strip()

    @field_validator("primary_key", mode="before")
    @classmethod
    def coerce_primary_key_to_list(cls, value: str | list[str] | None) -> list[str]:
        """Coerce primary_key to list if string is provided."""
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value else []
        return list(value)

    def to_domain(self) -> PipelineIdentity:
        """Convert to domain value object aggregate.

        Returns:
            PipelineIdentity: Rich domain model with Value Objects.

        Example:
            >>> config = PipelineIdentityConfig(
            ...     pipeline_id="chembl_activity_v1",
            ...     provider="chembl",
            ...     entity="activity",
            ...     primary_key=["activity_id"]
            ... )
            >>> identity = config.to_domain()
            >>> isinstance(identity.pipeline_id, PipelineId)
            True
        """
        # Lazy imports to avoid circular dependencies
        from bioetl.domain.aggregates.pipeline_identity import PipelineIdentity
        from bioetl.domain.providers import ProviderId
        from bioetl.domain.value_objects import EntityName, PipelineId

        return PipelineIdentity(
            pipeline_id=PipelineId(self.pipeline_id),
            provider=ProviderId(self.provider),
            entity=EntityName(self.entity),
            primary_key=tuple(self.primary_key),
        )


__all__ = ["PipelineIdentityConfig"]
