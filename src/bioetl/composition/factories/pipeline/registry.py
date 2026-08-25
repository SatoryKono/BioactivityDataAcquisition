"""Consolidated pipeline factory definitions and registration helpers."""

from __future__ import annotations

import threading
from typing import cast

from bioetl.composition.factories.pipeline._registry_factory_catalog import (
    LazyFactoryCatalog,
    list_pipeline_names,
)
from bioetl.composition.factories.pipeline.registry_manifest import (
    PIPELINE_CONFIGS as PIPELINE_CONFIGS,
)
from bioetl.composition.factories.pipeline.registry_core import (
    PipelineDefinition as PipelineDefinition,
    PipelineRegistry as PipelineRegistry,
    create_registry as create_registry,
    get_default_registry as get_default_registry,
)
from bioetl.composition.factories.pipeline.registry_exports import (
    FACTORY_EXPORTS,
    REGISTRY_PUBLIC_EXPORTS,
)
from bioetl.application.ports import PipelineRegistryProtocol
from bioetl.domain.ports import PipelineFactoryPort


_factories = LazyFactoryCatalog()


class PipelineFactoryRegistrationState:
    """Thread-safe default-registration state holder.

    This keeps mutable registration state instance-scoped and lazily created,
    mirroring the project-wide registry hardening pattern without changing the
    existing module-level helper API.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._registered = False


def create_pipeline_registration_state() -> PipelineFactoryRegistrationState:
    """Create isolated pipeline registration state for explicit composition seams."""
    return PipelineFactoryRegistrationState()


_default_registration_state: PipelineFactoryRegistrationState | None = None
_default_registration_state_lock = threading.RLock()


def _get_default_registration_state() -> PipelineFactoryRegistrationState:
    """Get the lazy default registration-state singleton (thread-safe)."""
    global _default_registration_state
    if _default_registration_state is not None:
        return _default_registration_state
    with _default_registration_state_lock:
        if _default_registration_state is None:
            _default_registration_state = create_pipeline_registration_state()
        return _default_registration_state


def _register_to_explicit_registry(registry: PipelineRegistryProtocol) -> None:
    """Register factories into an explicit registry instance."""
    _register_factories_to(registry)


def register_all_pipelines(
    registry: PipelineRegistryProtocol | None = None,
    *,
    registration_state: PipelineFactoryRegistrationState | None = None,
) -> None:
    """Explicitly register all pipeline factories with PipelineRegistry.

    Registration against the same explicit registry is safe to repeat:
    already-registered pipeline names are skipped and only missing factories
    are added.

    Args:
        registry: Explicit PipelineRegistry instance. ``None`` is rejected.
        registration_state: Optional idempotency state for test observation.

    Should be called once at application startup (e.g., in cli.py or bootstrap.py).
    """
    if registry is None:
        raise ValueError("register_all_pipelines requires an explicit registry")
    state = (
        registration_state
        if registration_state is not None
        else _get_default_registration_state()
    )
    with state._lock:
        _register_to_explicit_registry(registry)
        state._registered = True


def _register_factories_to(registry: PipelineRegistryProtocol) -> None:
    """Register all factory instances to the given registry.

    Internal helper for register_all_pipelines().
    Uses loop over _factories dict for DRY registration.

    Args:
        registry: Target registry instance.
    """
    registered_pipelines = set(registry.list_pipelines())
    for pipeline_name, factory in _factories.items():
        if pipeline_name in registered_pipelines:
            continue
        registry.register_factory(cast("PipelineFactoryPort", factory))


def _list_pipeline_names() -> list[str]:
    """Return available pipeline names in canonical sorted order."""
    return list_pipeline_names()


def is_registered(
    registration_state: PipelineFactoryRegistrationState | None = None,
) -> bool:
    """Check if factories have been registered.

    Thread-safe check of registration state.

    Returns:
        True if register_all_pipelines() has been called.
    """
    state = (
        registration_state
        if registration_state is not None
        else _get_default_registration_state()
    )
    return state._registered


def reset_registration(
    registry: PipelineRegistryProtocol | None = None,
    *,
    registration_state: PipelineFactoryRegistrationState | None = None,
) -> None:
    """Reset registration state (for testing only).

    Thread-safe reset of registration state and an explicit PipelineRegistry.
    WARNING: Only use in tests. Not for production.

    Note: For isolated tests, prefer creating a new registry instance with
    create_registry() rather than using reset_registration().
    """
    if registry is None:
        raise ValueError("reset_registration requires an explicit registry")
    state = (
        registration_state
        if registration_state is not None
        else _get_default_registration_state()
    )
    with state._lock:
        registry.clear()
        state._registered = False


def get_factory(pipeline_name: str) -> object:
    """Get a pipeline factory by name.

    Convenience function for accessing factories without going through registry.

    Args:
        pipeline_name: Name of the pipeline (e.g., "chembl_activity")

    Returns:
        GenericPipelineFactory instance

    Raises:
        KeyError: If pipeline_name is not found
    """
    if pipeline_name not in _factories:
        available = _list_pipeline_names()
        raise KeyError(f"Unknown pipeline: {pipeline_name}. Available: {available}")
    return _factories[pipeline_name]


def list_available_pipelines() -> list[str]:
    """List all available pipeline names.

    Returns:
        Sorted list of pipeline names
    """
    return _list_pipeline_names()


def __getattr__(name: str) -> object:
    """Resolve backward-compatible module-level factory exports lazily."""
    if name in FACTORY_EXPORTS:
        return _factories[FACTORY_EXPORTS[name]]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = REGISTRY_PUBLIC_EXPORTS
