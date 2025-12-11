"""Application layer ports for hexagonal architecture.

This module defines abstract ports (interfaces) that the application layer
uses to communicate with infrastructure. Concrete implementations (adapters)
are provided by the infrastructure layer and injected at composition time.

Note:
    Most ports have been moved to domain.ports to allow infrastructure
    adapters to implement them without depending on application layer.
    Only application-specific ports remain here.

Ports defined here:
- ObservabilityFactoryPortABC: Creating observability components
"""

from bioetl.application.ports.observability_factory_port import (
    ObservabilityFactoryPortABC,
)

# Re-export domain ports for backward compatibility
from bioetl.domain.ports.config_loader_port import (
    ConfigLoaderPortABC,
    ConfigPathResolverPortABC,
)
from bioetl.domain.ports.infrastructure_factory_port import (
    ABCRegistryResolverPortABC,
    InfrastructureFactoryPortABC,
)

__all__ = [
    "ABCRegistryResolverPortABC",
    "ConfigLoaderPortABC",
    "ConfigPathResolverPortABC",
    "InfrastructureFactoryPortABC",
    "ObservabilityFactoryPortABC",
]
