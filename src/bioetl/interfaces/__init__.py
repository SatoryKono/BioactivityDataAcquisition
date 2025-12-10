"""Interface layer package.

This layer contains adapters for external communication:
- CLI (Typer-based command line interface)
- REST (FastAPI-based HTTP API)
- Monitoring (Prometheus metrics export)

The interfaces layer depends on:
- application layer (use cases, orchestration)
- infrastructure layer (through CompositionRoot)

The interfaces layer should NOT contain business logic.
All orchestration happens in application layer.

Example usage:
    # CLI
    from bioetl.interfaces.cli import app
    app()

    # REST
    from bioetl.interfaces.rest import create_rest_app
    app = create_rest_app()

    # Composition Root (for custom wiring)
    from bioetl.interfaces import CompositionRoot
    root = CompositionRoot()
    container = root.create_pipeline_container(config)
"""

from bioetl.interfaces.composition_root import (
    CompositionRoot,
    ObservabilityStack,
    build_default_container,
    create_config_loader,
    create_config_path_resolver,
    get_composition_root,
    reset_composition_root,
)

__all__ = [
    # Core classes
    "CompositionRoot",
    "ObservabilityStack",
    # Singleton access
    "get_composition_root",
    "reset_composition_root",
    # Convenience functions
    "build_default_container",
    "create_config_loader",
    "create_config_path_resolver",
]
