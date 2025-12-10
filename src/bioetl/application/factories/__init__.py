"""
Application factories package.

Provides factories for creating pipeline services and components.
"""

from bioetl.application.factories.hooks import PipelineHookFactory
from bioetl.application.factories.noop import (
    create_noop_logger,
    create_noop_metadata_builder,
    create_noop_metrics_port,
    create_noop_validator_factory,
)
from bioetl.application.factories.record_source import RecordSourceFactory
from bioetl.application.factories.service_factory import (
    ApplicationServiceFactory,
    ApplicationServiceFactoryABC,
)
from bioetl.application.factories.services import ProviderServiceFactory

__all__ = [
    "ApplicationServiceFactory",
    "ApplicationServiceFactoryABC",
    "PipelineHookFactory",
    "ProviderServiceFactory",
    "RecordSourceFactory",
    "create_noop_logger",
    "create_noop_metadata_builder",
    "create_noop_metrics_port",
    "create_noop_validator_factory",
]
