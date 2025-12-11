"""Pipeline manifest - root aggregate for decomposed pipeline configuration.

This module defines PipelineManifest, the new top-level aggregate that
replaces the monolithic PipelineConfig with composed bounded contexts.

Migration path:
    PipelineConfig (monolithic) -> PipelineManifest (decomposed)

Each aggregate in PipelineManifest represents a bounded context:
- identity: WHAT pipeline (identification and metadata)
- data_flow: WHERE data flows (source -> sink)
- execution: HOW to execute (stages, runtime, transform)
- quality: Quality control settings
- provider_config: Provider-specific settings (optional)

Note: Observability and features are NOT part of the manifest.
These cross-cutting concerns should be injected via DI at runtime,
as they are infrastructure concerns, not domain configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bioetl.domain.configs.data_flow import DataFlowConfig
from bioetl.domain.configs.execution import ExecutionConfig
from bioetl.domain.configs.identity import PipelineIdentityConfig
from bioetl.domain.configs.pipeline import (
    ProviderConfigUnion,
    QualityConfig,
)

if TYPE_CHECKING:
    from bioetl.domain.configs.pipeline import PipelineConfig


class PipelineManifest(BaseModel):
    """Root aggregate for pipeline configuration.

    Replaces monolithic PipelineConfig with composed aggregates.
    Each aggregate represents a bounded context:
    - identity: WHAT pipeline (identification)
    - data_flow: WHERE data flows (source -> sink)
    - execution: HOW to execute (stages, runtime, transform)
    - quality: Quality control settings
    - provider_config: Provider-specific settings (optional)

    Note: observability and features are injected via DI, not part of manifest.
    These are runtime/infrastructure concerns that don't belong in domain config.

    Attributes:
        identity: Pipeline identification and metadata (pipeline_id, provider, entity).
        data_flow: Data source and sink aggregate.
        execution: Execution configuration (stages, runtime, transform).
        quality: Quality control, hashing, normalization, determinism settings.
        provider_config: Provider-specific configuration (ChEMBL, Dummy, etc).
        fields: Schema configuration for output fields.

    Example:
        >>> manifest = PipelineManifest(
        ...     identity=PipelineIdentityConfig(
        ...         pipeline_id="chembl.activity",
        ...         provider="chembl",
        ...         entity="activity"
        ...     ),
        ...     data_flow=DataFlowConfig(
        ...         source=DataSourceConfig(input_mode="auto_detect"),
        ...         sink=DataSinkConfig(output_path="./output")
        ...     ),
        ...     execution=ExecutionConfig(),
        ...     quality=QualityConfig()
        ... )

    See Also:
        PipelineConfig: Legacy config class with backward compatibility.
        PipelineConfig.to_manifest(): Convert from legacy to manifest.
        PipelineManifest.to_pipeline_config(): Convert from manifest to legacy.
    """

    identity: PipelineIdentityConfig = Field(
        ...,
        description="Pipeline identification (WHAT pipeline)",
    )
    data_flow: DataFlowConfig = Field(
        ...,
        description="Data flow configuration (WHERE data flows)",
    )
    execution: ExecutionConfig = Field(
        default_factory=ExecutionConfig,
        description="Execution configuration (HOW to execute)",
    )
    quality: QualityConfig = Field(
        default_factory=QualityConfig,
        description="Quality control settings",
    )
    provider_config: ProviderConfigUnion | None = Field(
        default=None,
        description="Provider-specific configuration",
    )
    fields: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Schema configuration for output fields",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    # =========================================================================
    # Validators
    # =========================================================================

    @model_validator(mode="after")
    def validate_provider_alignment(self) -> PipelineManifest:
        """Ensure provider_config provider aligns with identity.provider."""
        if self.provider_config is not None:
            if self.provider_config.provider != self.identity.provider:
                raise ValueError(
                    f"provider_config.provider ({self.provider_config.provider}) "
                    f"must match identity.provider ({self.identity.provider})"
                )
        return self

    # =========================================================================
    # Convenience properties (shortcuts to nested attributes)
    # =========================================================================

    @property
    def pipeline_id(self) -> str:
        """Shortcut to identity.pipeline_id."""
        return str(self.identity.pipeline_id)

    @property
    def provider(self) -> str:
        """Shortcut to identity.provider."""
        return str(self.identity.provider)

    @property
    def entity(self) -> str:
        """Shortcut to identity.entity."""
        return str(self.identity.entity)

    @property
    def source(self) -> Any:
        """Shortcut to data_flow.source."""
        return self.data_flow.source

    @property
    def sink(self) -> Any:
        """Shortcut to data_flow.sink."""
        return self.data_flow.sink

    @property
    def stages(self) -> Any:
        """Shortcut to execution.stages."""
        return self.execution.stages

    @property
    def runtime(self) -> Any:
        """Shortcut to execution.runtime."""
        return self.execution.runtime

    @property
    def transform(self) -> Any:
        """Shortcut to execution.transform."""
        return self.execution.transform

    # =========================================================================
    # Conversion methods
    # =========================================================================

    def to_pipeline_config(self) -> PipelineConfig:
        """Convert to legacy PipelineConfig for backward compatibility.

        This method allows gradual migration from PipelineManifest to code
        that still expects PipelineConfig.

        Returns:
            PipelineConfig: Legacy configuration object with all fields populated.

        Example:
            >>> manifest = PipelineManifest(...)
            >>> legacy_config = manifest.to_pipeline_config()
            >>> # Use legacy_config with existing code
        """
        from bioetl.domain.configs.pipeline import (
            FeatureFlagsConfig,
            ObservabilityConfig,
            PipelineConfig,
        )

        return PipelineConfig(
            identity=self.identity,
            data_flow=self.data_flow,
            stages=self.execution.stages,
            runtime=self.execution.runtime,
            transform=self.execution.transform,
            quality=self.quality,
            provider_config=self.provider_config,
            fields=self.fields,
            # Use defaults for DI-injected concerns
            observability=ObservabilityConfig(),
            features=FeatureFlagsConfig(),
        )

    @classmethod
    def from_pipeline_config(cls, config: PipelineConfig) -> PipelineManifest:
        """Create PipelineManifest from legacy PipelineConfig.

        This factory method enables migration from existing PipelineConfig
        instances to the new PipelineManifest format.

        Args:
            config: Legacy PipelineConfig instance.

        Returns:
            PipelineManifest: New manifest with decomposed configuration.

        Note:
            observability and features from PipelineConfig are NOT transferred
            to the manifest, as these should be injected via DI at runtime.

        Example:
            >>> legacy_config = PipelineConfig(...)
            >>> manifest = PipelineManifest.from_pipeline_config(legacy_config)
        """
        return cls(
            identity=config.identity,
            data_flow=config.data_flow,
            execution=ExecutionConfig(
                stages=config.stages,
                runtime=config.runtime,
                transform=config.transform,
            ),
            quality=config.quality,
            provider_config=config.provider_config,
            fields=config.fields,
        )


__all__ = ["PipelineManifest"]
