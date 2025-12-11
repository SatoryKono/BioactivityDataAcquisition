"""
Pipelines package.

Provides base pipeline implementation and factory registry.

Public API:
    - PipelineBase: Abstract base class for all pipelines
    - Registry functions: get_factory, get_pipeline_factory, etc.

For contracts (PipelineContainerABC, PipelineFactoryABC),
import from bioetl.application.contracts.
"""

from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.registry import (
    get_factory,
    get_pipeline_class,
    get_pipeline_factory,
    get_registered_factories,
    list_pipelines,
)

__all__ = [
    # Base class
    "PipelineBase",
    # Factory functions
    "get_factory",
    "get_pipeline_class",
    "get_pipeline_factory",
    "get_registered_factories",
    "list_pipelines",
]
