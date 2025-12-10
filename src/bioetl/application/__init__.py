"""
Application layer — orchestration and use cases.

This layer coordinates domain logic and infrastructure adapters.
It contains no business rules (those are in domain) and no I/O details
(those are in infrastructure).

Key components:
    PipelineOrchestrator: Entry point for pipeline execution and assembly.
    PipelineContainer: DI container for pipeline dependencies.
    ApplicationBootstrap: Application lifecycle and dependency wiring.
    Factories: Create specialized services and components.

Typical usage::

    from bioetl.application import PipelineOrchestrator, create_application_bootstrap

    bootstrap = create_application_bootstrap(config_path)
    orchestrator = PipelineOrchestrator(pipeline_name, config, ...)
    result = orchestrator.run_pipeline()
"""

from bioetl.application.bootstrap import (
    ApplicationBootstrap,
    ApplicationContext,
    ConfigLoaderFactory,
    ProviderClearer,
    ProviderInjector,
    create_application_bootstrap,
)
from bioetl.application.container import (
    PipelineContainer,
    create_default_container_factory,
)
from bioetl.application.contracts import PipelineContainerABC, PipelineFactoryABC
from bioetl.application.orchestrator import PipelineOrchestrator

__all__ = [
    "ApplicationBootstrap",
    "ApplicationContext",
    "ConfigLoaderFactory",
    "PipelineContainer",
    "PipelineContainerABC",
    "PipelineFactoryABC",
    "PipelineOrchestrator",
    "ProviderClearer",
    "ProviderInjector",
    "create_application_bootstrap",
    "create_default_container_factory",
]
