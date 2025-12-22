"""Deprecated: Pipeline Registry has moved to composition layer.

This module acts as a proxy for backward compatibility.
Please update imports to: from bioetl.composition.registry import PipelineRegistry
"""

import warnings
import pyarrow as pa
from typing import Any

from bioetl.composition.registry import (
    PipelineDefinition,
    PipelineFactoryProtocol,
    PipelineRegistry as NewPipelineRegistry,
)

# Re-export types for compatibility
__all__ = [
    "PipelineDefinition",
    "PipelineFactoryProtocol",
    "PipelineRegistry",
]


class PipelineRegistry:
    """Deprecated PipelineRegistry proxy.

    Delegates to bioetl.composition.registry.PipelineRegistry.
    """

    @classmethod
    def register(
        cls,
        pipeline_name: str,
        factory: type[Any],
        silver_schema: pa.Schema | None = None,
        gold_schema: Any | None = None,
    ) -> None:
        """Register a pipeline factory (deprecated)."""
        warnings.warn(
            "bioetl.application.registry.PipelineRegistry is deprecated. "
            "Use bioetl.composition.registry.PipelineRegistry instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        NewPipelineRegistry.register(
            pipeline_name,
            factory,
            silver_schema,
            gold_schema
        )

    @classmethod
    def register_factory(
        cls,
        factory: PipelineFactoryProtocol,
    ) -> None:
        """Register a pipeline factory instance (deprecated)."""
        warnings.warn(
            "bioetl.application.registry.PipelineRegistry is deprecated. "
            "Use bioetl.composition.registry.PipelineRegistry instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        NewPipelineRegistry.register_factory(factory)

    @classmethod
    def get(cls, pipeline_name: str) -> PipelineDefinition:
        """Get pipeline definition (deprecated)."""
        warnings.warn(
            "bioetl.application.registry.PipelineRegistry is deprecated. "
            "Use bioetl.composition.registry.PipelineRegistry instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return NewPipelineRegistry.get(pipeline_name)

    @classmethod
    def list_pipelines(cls) -> list[str]:
        """List registered pipelines (deprecated)."""
        warnings.warn(
            "bioetl.application.registry.PipelineRegistry is deprecated. "
            "Use bioetl.composition.registry.PipelineRegistry instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return NewPipelineRegistry.list_pipelines()
