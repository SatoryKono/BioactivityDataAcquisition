# mypy: disable-error-code="misc,untyped-decorator"
"""Pydantic schemas for composite pipeline configuration files.

Validates composite pipeline YAML files (configs/composites/*.yaml)
before converting to domain objects. Implements ADR-026 Composite Pipeline Pattern.

Usage:
    >>> schema = CompositeConfigFileSchema.model_validate(yaml_data)
    >>> domain_config = schema.to_domain()
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field, model_validator

from bioetl.domain.composite import CompositeConfig
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.schemas._composite_config_merge_schema import (
    ColumnGroupSchema,
    MergeOutputSchema,
    MergeSchema,
    MergeSortBySchema,
)
from bioetl.infrastructure.schemas.composite_config_base import (
    AggregationFieldSchema,
    AggregationSchema,
    DependencySchema,
    EnricherSchema,
    SeedSchema,
)
from bioetl.infrastructure.schemas.composite_validation import (
    CompositeDQSchema,
    CrossValidationSchema,
    DQOverrideSchema,
    EnricherFieldPairingSchema,
    ExecutionSchema,
    FieldComparisonSpecSchema,
    LineageSchema,
    RetrySchema,
)


class CompositeConfigSchema(BaseModel):
    """Pydantic schema for complete composite pipeline configuration.

    Validates structural/types contract for the 'composite' YAML section and
    converts to domain CompositeConfig.

    Business invariants (join-key compatibility, uniqueness, etc.) are owned by
    the domain layer and enforced via delegated validation.
    """

    name: str = Field(..., min_length=1, description="Composite pipeline name")
    version: str = Field(
        ..., min_length=1, description="Configuration version (semver)"
    )
    seed: SeedSchema = Field(..., description="Seed pipeline configuration")
    dependencies: list[DependencySchema] = Field(
        default_factory=list,
        description="List of dependency configurations (run after seed, before enrichers)",
    )
    enrichers: list[EnricherSchema] = Field(
        default_factory=list,
        description="List of enricher configurations (optional if dependencies provided)",
    )
    merge: MergeSchema = Field(..., description="Merge step configuration")
    dq_overrides: CompositeDQSchema = Field(
        default_factory=CompositeDQSchema,
        description="Data quality configuration",
    )
    execution: ExecutionSchema = Field(
        default_factory=ExecutionSchema, description="Execution options"
    )
    lineage: LineageSchema = Field(
        default_factory=LineageSchema, description="Lineage tracking configuration"
    )
    cross_validation: CrossValidationSchema = Field(
        default_factory=CrossValidationSchema,
        description="Cross-validation configuration for pre-merge checks",
    )

    @model_validator(mode="after")
    def validate_domain_invariants(self) -> Self:
        """Delegate business invariant checks to domain CompositeConfig.

        Keeps infrastructure schema focused on structural/type validation and
        conversion while preserving ValidationError UX at schema boundary.
        """
        try:
            self.to_domain()
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        return self

    def to_domain(self) -> CompositeConfig:
        """Convert to immutable domain CompositeConfig.

        Returns:
            The CompositeConfig result.
        """
        return CompositeConfig(
            name=self.name,
            version=self.version,
            seed=self.seed.to_domain(),
            dependencies=tuple(d.to_domain() for d in self.dependencies),
            enrichers=tuple(e.to_domain() for e in self.enrichers),
            merge=self.merge.to_domain(),
            dq=self.dq_overrides.to_domain(),
            execution=self.execution.to_domain(),
            lineage=self.lineage.to_domain(),
            cross_validation=self.cross_validation.to_domain(),
        )


class CompositeConfigFileSchema(BaseModel):
    """Pydantic schema for complete composite configuration file.

    Validates the entire YAML file structure including schema_version
    and maintenance metadata.
    """

    schema_version: str = Field(
        default="2.0.0", description="Schema version for file format"
    )
    composite: CompositeConfigSchema = Field(
        ..., description="The composite pipeline configuration"
    )
    gold_filters: JsonDict | None = Field(
        default=None,
        description="Deprecated legacy field; composite-local gold_filters are unsupported",
    )
    maintenance: JsonDict | None = (  # Any: YAML config has heterogeneous values
        Field(  # Any: YAML config has heterogeneous values
            default=None, description="Optional maintenance configuration"
        )
    )

    @model_validator(mode="after")
    def reject_composite_local_gold_filters(self) -> Self:
        """Reject unsupported top-level composite gold_filters with a clear error."""
        if self.gold_filters is not None:
            raise ValueError(
                "Composite-local top-level gold_filters are unsupported; "
                "move filtering policy to entity pipeline configs or implement "
                "explicit runtime support first."
            )
        return self

    def to_domain(self) -> CompositeConfig:
        """Convert to immutable domain CompositeConfig.

        Returns:
            The CompositeConfig result.
        """
        return self.composite.to_domain()


def validate_composite_config_payload(
    payload: JsonDict,  # Any: YAML config has heterogeneous values
) -> CompositeConfigFileSchema:
    """Validate composite YAML payload against the canonical strict contract.

    Runtime and generated JSON Schema both use :class:`CompositeConfigFileSchema`
    as the canonical contract. Files that omit ``composite.version`` are no
    longer part of the active runtime contract and must fail validation.

    Args:
        payload: Data payload.

    Returns:
        Validated CompositeConfigFileSchema.
    """

    result: CompositeConfigFileSchema = CompositeConfigFileSchema.model_validate(
        payload
    )
    return result


__all__ = [
    "AggregationFieldSchema",
    "AggregationSchema",
    "ColumnGroupSchema",
    "CompositeConfigFileSchema",
    "CompositeConfigSchema",
    "CompositeDQSchema",
    "CrossValidationSchema",
    "DQOverrideSchema",
    "DependencySchema",
    "EnricherFieldPairingSchema",
    "EnricherSchema",
    "ExecutionSchema",
    "FieldComparisonSpecSchema",
    "LineageSchema",
    "MergeOutputSchema",
    "MergeSchema",
    "MergeSortBySchema",
    "RetrySchema",
    "SeedSchema",
    "validate_composite_config_payload",
]
