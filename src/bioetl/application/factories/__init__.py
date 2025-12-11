"""
Application factories package.

Provides factories for creating pipeline services and components.

Public factories:
    - ApplicationServiceFactory / ApplicationServiceFactoryABC
    - PipelineHookFactory
    - PipelineRuntimeFactory / PipelineRuntimeFactoryABC
    - ProviderServiceFactory / ProviderServiceFactoryABC
    - RecordSourceFactory / RecordSourceFactoryABC
    - TransformComponentFactory / TransformComponentFactoryABC

No-op factories (for testing/fallback):
    - create_noop_logger
    - create_noop_metadata_builder
    - create_noop_metrics_port
    - create_noop_validator_factory
"""

from bioetl.application.factories.hooks import (
    PipelineHookFactory,
    PipelineHookFactoryABC,
)
from bioetl.application.factories.noop import (
    create_noop_logger,
    create_noop_metadata_builder,
    create_noop_metrics_port,
    create_noop_validator_factory,
)
from bioetl.application.factories.record_source import (
    RecordSourceFactory,
    RecordSourceFactoryABC,
)
from bioetl.application.factories.runtime_factory import (
    PipelineRuntimeFactory,
    PipelineRuntimeFactoryABC,
)
from bioetl.application.factories.service_factory import (
    ApplicationServiceFactory,
    ApplicationServiceFactoryABC,
)
from bioetl.application.factories.services import (
    ProviderServiceFactory,
    ProviderServiceFactoryABC,
)
from bioetl.application.factories.transform_factory import (
    TransformComponentFactory,
    TransformComponentFactoryABC,
)

__all__ = [
    # Service factories
    "ApplicationServiceFactory",
    "ApplicationServiceFactoryABC",
    "PipelineHookFactory",
    "PipelineHookFactoryABC",
    "PipelineRuntimeFactory",
    "PipelineRuntimeFactoryABC",
    "ProviderServiceFactory",
    "ProviderServiceFactoryABC",
    "RecordSourceFactory",
    "RecordSourceFactoryABC",
    "TransformComponentFactory",
    "TransformComponentFactoryABC",
    # No-op factories
    "create_noop_logger",
    "create_noop_metadata_builder",
    "create_noop_metrics_port",
    "create_noop_validator_factory",
]
