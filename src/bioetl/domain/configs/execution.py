"""Execution configuration aggregate.

This module defines the ExecutionConfig aggregate that groups all settings
related to HOW a pipeline executes, as opposed to WHAT it processes.

Design Decision: TransformConfig is kept separate from PipelineStagesConfig
----------------------------------------------------------------------
While both relate to the transform stage, they serve different purposes:

1. PipelineStagesConfig answers "WHICH stages should run?" (boolean flags)
   - extract: bool | None - Should we fetch data?
   - transform: bool | None - Should we transform data?
   - load: bool | None - Should we persist data?

2. TransformConfig answers "HOW should transform work?" (behavioral settings)
   - serialization_mode: "json" | "flat" | "pipe"

These are orthogonal concerns:
- You might enable transform (stages.transform=True) with different serialization modes
- The stage flag is about activation, the config is about behavior
- Mixing them would violate Single Responsibility Principle

The ExecutionConfig aggregate unifies these under a single cohesive boundary
while preserving their distinct responsibilities.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.configs.pipeline import PipelineStagesConfig, RuntimeConfig
from bioetl.domain.configs.transform import TransformConfig

__all__ = ["ExecutionConfig"]


class ExecutionConfig(BaseModel):
    """Aggregate for pipeline execution settings.

    Groups all configuration that affects HOW a pipeline runs:
    - stages: Which ETL phases are enabled (extract/transform/load)
    - runtime: Execution parameters (pagination, HTTP, storage, CSV)
    - transform: Transform stage behavior (serialization mode)

    This aggregate provides a unified interface for execution-related
    settings while maintaining immutability for thread-safety.

    Example:
        ```python
        execution = ExecutionConfig(
            stages=PipelineStagesConfig(extract=True, transform=True, load=False),
            runtime=RuntimeConfig(pagination=PaginationConfig(limit=500)),
            transform=TransformConfig(serialization_mode="flat"),
        )

        if execution.is_extract_enabled:
            # Run extraction with batch size
            batch_size = execution.effective_batch_size
        ```
    """

    stages: PipelineStagesConfig = Field(
        default_factory=PipelineStagesConfig,
        description="ETL stage activation flags",
    )
    runtime: RuntimeConfig = Field(
        default_factory=RuntimeConfig,
        description="Runtime execution parameters",
    )
    transform: TransformConfig = Field(
        default_factory=TransformConfig,
        description="Transform stage behavioral settings",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- Stage activation properties ---

    @property
    def is_extract_enabled(self) -> bool:
        """Check if extract stage is enabled.

        Returns True unless explicitly disabled (stages.extract=False).
        None means auto-detect, which defaults to enabled.
        """
        return self.stages.extract is not False

    @property
    def is_transform_enabled(self) -> bool:
        """Check if transform stage is enabled.

        Returns True unless explicitly disabled (stages.transform=False).
        None means auto-detect, which defaults to enabled.
        """
        return self.stages.transform is not False

    @property
    def is_load_enabled(self) -> bool:
        """Check if load stage is enabled.

        Returns True unless explicitly disabled (stages.load=False).
        None means auto-detect, which defaults to enabled.
        """
        return self.stages.load is not False

    # --- Computed runtime properties ---

    @property
    def effective_batch_size(self) -> int:
        """Compute effective batch size from runtime pagination config.

        This is the primary batch size used for data fetching operations.
        """
        return self.runtime.pagination.limit

    @property
    def serialization_mode(self) -> str:
        """Shortcut for transform.serialization_mode.

        Returns the canonical serialization format for nested fields.
        One of: "json", "flat", "pipe"
        """
        return self.transform.serialization_mode

    # --- HTTP settings shortcuts ---

    @property
    def request_timeout(self) -> float:
        """Request timeout in seconds from HTTP config."""
        return self.runtime.http.timeout

    @property
    def max_retries(self) -> int:
        """Maximum retry attempts from HTTP config."""
        return self.runtime.http.max_retries

    # --- Factory methods ---

    @classmethod
    def with_stages(
        cls,
        *,
        extract: bool | None = None,
        transform: bool | None = None,
        load: bool | None = None,
        runtime: RuntimeConfig | None = None,
        transform_config: TransformConfig | None = None,
    ) -> ExecutionConfig:
        """Create ExecutionConfig with specific stage settings.

        Convenience factory for common configuration patterns.

        Args:
            extract: Enable/disable extract stage (None = auto-detect)
            transform: Enable/disable transform stage (None = auto-detect)
            load: Enable/disable load stage (None = auto-detect)
            runtime: Runtime configuration (uses defaults if None)
            transform_config: Transform configuration (uses defaults if None)

        Returns:
            New ExecutionConfig instance
        """
        return cls(
            stages=PipelineStagesConfig(
                extract=extract,
                transform=transform,
                load=load,
            ),
            runtime=runtime or RuntimeConfig(),
            transform=transform_config or TransformConfig(),
        )

    @classmethod
    def extract_only(cls, *, runtime: RuntimeConfig | None = None) -> ExecutionConfig:
        """Create config for extract-only pipeline.

        Enables only the extract stage, disabling transform and load.
        """
        return cls.with_stages(
            extract=True,
            transform=False,
            load=False,
            runtime=runtime,
        )

    @classmethod
    def transform_only(
        cls,
        *,
        runtime: RuntimeConfig | None = None,
        transform_config: TransformConfig | None = None,
    ) -> ExecutionConfig:
        """Create config for transform-only pipeline.

        Enables only the transform stage, disabling extract and load.
        """
        return cls.with_stages(
            extract=False,
            transform=True,
            load=False,
            runtime=runtime,
            transform_config=transform_config,
        )

    @classmethod
    def full_pipeline(
        cls,
        *,
        runtime: RuntimeConfig | None = None,
        transform_config: TransformConfig | None = None,
    ) -> ExecutionConfig:
        """Create config for full ETL pipeline.

        Explicitly enables all stages.
        """
        return cls.with_stages(
            extract=True,
            transform=True,
            load=True,
            runtime=runtime,
            transform_config=transform_config,
        )
