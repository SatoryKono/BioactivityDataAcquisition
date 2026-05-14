"""Consolidated pipeline factory definitions and registration helpers."""

from __future__ import annotations

import threading
from importlib import import_module
from types import MappingProxyType
from typing import Protocol, cast

from bioetl.application.core.wiring.registry import GenericPipeline
from bioetl.composition.factories.pipeline.assembler import (
    GenericPipelineFactory,
)
from bioetl.composition.factories.pipeline.contract_validator import create_factory
from bioetl.composition.factories.pipeline.registry_manifest import (
    PIPELINE_CONFIGS,
)
from bioetl.composition.registry_default import get_default_registry
from bioetl.domain.ports import PipelineFactoryPort

_registry_module = import_module("bioetl.composition.registry")
PipelineDefinition = _registry_module.PipelineDefinition
PipelineRegistry = _registry_module.PipelineRegistry
create_registry = _registry_module.create_registry


class PipelineRegistryProtocol(Protocol):
    """Minimal pipeline registry contract required for factory registration."""

    def list_pipelines(self) -> list[str]:
        """Return registered pipeline names."""
        ...

    def register_factory(self, factory: PipelineFactoryPort) -> None:
        """Register one pipeline factory."""
        ...

    def clear(self) -> None:
        """Clear registered factories."""
        ...


def _build_factories() -> dict[str, GenericPipelineFactory[GenericPipeline]]:
    """Build factory instances from the canonical pipeline config table."""
    return {config.pipeline_name: create_factory(config) for config in PIPELINE_CONFIGS}


# Backward-compatible module surface kept for tests/importers, but frozen to
# avoid additional module-level mutable registry state.
_factories = MappingProxyType(_build_factories())

# Export individual factories for backward compatibility
chembl_activity_factory = _factories["chembl_activity"]
chembl_assay_factory = _factories["chembl_assay"]
chembl_assay_parameters_factory = _factories["chembl_assay_parameters"]
chembl_cell_line_factory = _factories["chembl_cell_line"]
chembl_compound_record_factory = _factories["chembl_compound_record"]
chembl_publication_factory = _factories["chembl_publication"]
chembl_publication_similarity_factory = _factories["chembl_publication_similarity"]
chembl_publication_term_factory = _factories["chembl_publication_term"]
chembl_molecule_factory = _factories["chembl_molecule"]
chembl_target_factory = _factories["chembl_target"]
chembl_target_component_factory = _factories["chembl_target_component"]
chembl_tissue_factory = _factories["chembl_tissue"]
chembl_subcellular_fraction_factory = _factories["chembl_subcellular_fraction"]
chembl_protein_class_factory = _factories["chembl_protein_class"]
pubchem_compound_factory = _factories["pubchem_compound"]
uniprot_protein_factory = _factories["uniprot_protein"]
uniprot_idmapping_factory = _factories["uniprot_idmapping"]
pubmed_publication_factory = _factories["pubmed_publication"]
crossref_publication_factory = _factories["crossref_publication"]
openalex_publication_factory = _factories["openalex_publication"]
semanticscholar_publication_factory = _factories["semanticscholar_publication"]


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


def _get_default_registration_state() -> PipelineFactoryRegistrationState:
    """Get the lazy default registration-state singleton."""
    global _default_registration_state
    if _default_registration_state is None:
        _default_registration_state = create_pipeline_registration_state()
    return _default_registration_state


def _register_to_explicit_registry(registry: PipelineRegistryProtocol) -> None:
    """Register factories into an explicit registry instance."""
    _register_factories_to(registry)


def _register_default_registry_once(
    registration_state: PipelineFactoryRegistrationState,
) -> None:
    """Register factories into the default registry exactly once."""
    if registration_state._registered:
        return
    with registration_state._lock:
        if registration_state._registered:
            return
        _register_factories_to(get_default_registry())
        registration_state._registered = True


def register_all_pipelines(
    registry: PipelineRegistryProtocol | None = None,
    *,
    registration_state: PipelineFactoryRegistrationState | None = None,
) -> None:
    """Explicitly register all pipeline factories with PipelineRegistry.

    This function is idempotent and thread-safe - calling it multiple times
    or from multiple threads has no effect after the first successful call.

    Uses double-checked locking pattern to minimize lock contention while
    ensuring thread-safe initialization.

    When called with a custom registry, registration is still safe to repeat:
    already-registered pipeline names are skipped and only missing factories
    are added.

    Args:
        registry: Optional PipelineRegistry instance. If None, uses the
            default global registry. Pass a custom registry for test isolation.
        registration_state: Optional explicit idempotency state for the default
            registry path. Pass one when composing isolated startup contexts.

    Should be called once at application startup (e.g., in cli.py or bootstrap.py).
    """
    if registry is not None:
        _register_to_explicit_registry(registry)
        return

    state = (
        registration_state
        if registration_state is not None
        else _get_default_registration_state()
    )
    _register_default_registry_once(state)


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
    return sorted(_factories.keys())


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

    Thread-safe reset of registration flag. Also clears the default PipelineRegistry.
    WARNING: Only use in tests. Not for production.

    Note: For isolated tests, prefer creating a new registry instance with
    create_registry() rather than using reset_registration().
    """
    state = (
        registration_state
        if registration_state is not None
        else _get_default_registration_state()
    )
    target_registry = registry if registry is not None else get_default_registry()
    with state._lock:
        target_registry.clear()
        state._registered = False


def get_factory(pipeline_name: str) -> GenericPipelineFactory[GenericPipeline]:
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


_PIPELINE_FACTORY_API = (
    get_factory,
    list_available_pipelines,
    reset_registration,
)

__all__ = [
    "PipelineDefinition",
    "PipelineFactoryRegistrationState",
    "PipelineRegistry",
    "chembl_activity_factory",
    "chembl_assay_factory",
    "chembl_assay_parameters_factory",
    "chembl_cell_line_factory",
    "chembl_compound_record_factory",
    "chembl_molecule_factory",
    "chembl_protein_class_factory",
    "chembl_publication_factory",
    "chembl_publication_similarity_factory",
    "chembl_publication_term_factory",
    "chembl_subcellular_fraction_factory",
    "chembl_target_component_factory",
    "chembl_target_factory",
    "chembl_tissue_factory",
    "create_pipeline_registration_state",
    "create_registry",
    "crossref_publication_factory",
    "get_factory",
    "is_registered",
    "list_available_pipelines",
    "openalex_publication_factory",
    "pubchem_compound_factory",
    "pubmed_publication_factory",
    "register_all_pipelines",
    "reset_registration",
    "semanticscholar_publication_factory",
    "uniprot_idmapping_factory",
    "uniprot_protein_factory",
]
