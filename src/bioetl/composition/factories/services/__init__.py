"""Services factory subpackage (DI for PipelineRunner)."""

from __future__ import annotations

from bioetl.composition.factories.pipeline._creation_wiring import (
    _BuildPipelineServicesFn,
    _create_pipeline_with_services_impl,
    _PipelineCreationInputs,
    _ServiceBundleDeps,
)
from bioetl.composition.factories.services.factory import (
    BaseServicesFactory,
    ServicesBuilder,
    create_data_normalization_service,
)
from bioetl.composition.factories.services.observability_api import (
    _create_cached_bronze_data_source,
    _create_data_source,
    create_shared_metrics,
)

__all__ = [
    "BaseServicesFactory",
    "ServicesBuilder",
    "_BuildPipelineServicesFn",
    "_PipelineCreationInputs",
    "_ServiceBundleDeps",
    "_create_cached_bronze_data_source",
    "_create_data_source",
    "_create_pipeline_with_services_impl",
    "create_data_normalization_service",
    "create_shared_metrics",
]
