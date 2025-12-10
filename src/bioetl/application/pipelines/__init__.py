"""
Pipelines package.

Provides base pipeline implementation, contracts, and factory registry.
"""

from bioetl.application.contracts import PipelineContainerABC, PipelineFactoryABC
from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.registry import (
    get_factory,
    get_pipeline_factory,
    get_registered_factories,
    get_registered_pipelines,
)

__all__ = [
    "PipelineBase",
    "PipelineContainerABC",
    "PipelineFactoryABC",
    "get_factory",
    "get_pipeline_factory",
    "get_registered_factories",
    "get_registered_pipelines",
]
