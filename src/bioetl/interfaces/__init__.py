"""Interface layer package.

This layer contains adapters for external communication:
- CLI (Typer-based command line interface)
- REST (FastAPI-based HTTP API)
- Monitoring (Prometheus metrics export)

The interfaces layer should NOT contain business logic.
All orchestration happens in application layer.
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
    create_config_path_resolver,
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
from bioetl.interfaces.context_manager import (
    application_context,
    get_current_context,
    reset_current_context,
    set_current_context,
)

__all__ = [
    # Application context
    "ApplicationContext",
    "get_application_context",
    "set_application_context",
    "reset_application_context",
    # Thread-safe context manager (recommended for tests)
    "application_context",
    "get_current_context",
    "set_current_context",
    "reset_current_context",
    # Composition root (backward compatible)
    "CompositionRoot",
    "ObservabilityStack",
    "build_default_container",
    "create_config_loader",
    "create_config_path_resolver",
    "get_composition_root",
    "reset_composition_root",
    # Factories
    "ObservabilityFactoryABC",
    "DefaultObservabilityFactory",
    "InfrastructureFactoryABC",
    "DefaultInfrastructureFactory",
    # Use case factory
    "UseCaseFactory",
    "get_use_case_factory",
    "reset_use_case_factory",
]
