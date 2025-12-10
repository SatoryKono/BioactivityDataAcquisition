"""Execution configuration - aggregate for runtime execution settings.

This module defines ExecutionConfig, which groups all execution-related
configuration into a single bounded context:
- stages: Which ETL stages to execute
- runtime: Execution parameters (pagination, HTTP, storage)
- transform: Transform-specific settings
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.configs.pipeline import (
    PaginationConfig,
    PipelineStagesConfig,
    RuntimeConfig,
)
from bioetl.domain.configs.transform import TransformConfig


class ExecutionConfig(BaseModel):
    """Aggregate for pipeline execution configuration.

    Groups execution-related settings into a single bounded context
    representing HOW the pipeline executes:
    - Which stages run (extract, transform, load)
    - Runtime parameters (pagination, HTTP client, storage)
    - Transform-specific settings

    This aggregate enforces that execution settings are coherent
    and provides a single point of configuration for pipeline execution.

    Attributes:
        stages: ETL stage flags (extract, transform, load).
        runtime: Execution runtime settings (pagination, http, storage, csv).
        transform: Transform stage specific settings.

    Example:
        >>> execution = ExecutionConfig(
        ...     stages=PipelineStagesConfig(extract=True, transform=True, load=False),
        ...     runtime=RuntimeConfig(
        ...         pagination=PaginationConfig(limit=500)
        ...     ),
        ...     transform=TransformConfig(serialization_mode="json")
        ... )
    """

    stages: PipelineStagesConfig = Field(
        default_factory=PipelineStagesConfig,
        description="ETL stage enable/disable flags",
    )
    runtime: RuntimeConfig = Field(
        default_factory=RuntimeConfig,
        description="Runtime execution settings",
    )
    transform: TransformConfig = Field(
        default_factory=TransformConfig,
        description="Transform stage settings",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    # =========================================================================
    # Convenience properties
    # =========================================================================

    @property
    def pagination(self) -> PaginationConfig:
        """Shortcut access to runtime.pagination."""
        return self.runtime.pagination

    @property
    def serialization_mode(self) -> str:
        """Shortcut access to transform.serialization_mode."""
        return self.transform.serialization_mode

    @property
    def extract_enabled(self) -> bool | None:
        """Whether extract stage is explicitly enabled/disabled."""
        return self.stages.extract

    @property
    def transform_enabled(self) -> bool | None:
        """Whether transform stage is explicitly enabled/disabled."""
        return self.stages.transform

    @property
    def load_enabled(self) -> bool | None:
        """Whether load stage is explicitly enabled/disabled."""
        return self.stages.load


__all__ = ["ExecutionConfig"]
