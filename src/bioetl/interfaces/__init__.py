"""Interface layer — adapters for CLI, REST, Monitoring.

This layer adapts external requests to application use cases.
It should NOT contain business logic.
"""

from bioetl.interfaces.application_context import (
    ApplicationContext,
    get_application_context,
    reset_application_context,
    set_application_context,
)
from bioetl.interfaces.composition_root import (
    CompositionRoot,
    ObservabilityStack,
    build_default_container,
    create_config_loader,
    get_composition_root,
    reset_composition_root,
)
from bioetl.interfaces.factories import (
    DefaultInfrastructureFactory,
    DefaultObservabilityFactory,
    InfrastructureFactoryABC,
    ObservabilityFactoryABC,
)
from bioetl.interfaces.use_case_factory import (
    UseCaseFactory,
    get_use_case_factory,
    reset_use_case_factory,
)

__all__ = [
    # Application context
    "ApplicationContext",
    "get_application_context",
    "set_application_context",
    "reset_application_context",
    # Composition root
    "CompositionRoot",
    "ObservabilityStack",
    "build_default_container",
    "create_config_loader",
    "get_composition_root",
    "reset_composition_root",
    # Factories
    "ObservabilityFactoryABC",
    "DefaultObservabilityFactory",
    "InfrastructureFactoryABC",
    "DefaultInfrastructureFactory",
    # Use cases
    "UseCaseFactory",
    "get_use_case_factory",
    "reset_use_case_factory",
]
