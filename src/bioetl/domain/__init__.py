"""Domain layer: entities, value objects, ports, and context objects.

This package provides the domain layer public API. Consumers should
import from the specific sub-facades for most symbols:

- ``bioetl.domain.ports``          — Protocol interfaces for DI
- ``bioetl.domain.exceptions``     — Domain-specific error hierarchy
- ``bioetl.domain.value_objects``  — Value objects and DQ report types
- ``bioetl.domain.types``          — Enums, type aliases
- ``bioetl.domain.entities``       — Rich domain objects
- ``bioetl.domain.config``         — Pipeline / runtime config
- ``bioetl.domain.normalization``  — Pure normalization functions
- ``bioetl.domain.transformations``— Pure hashing / DQ functions
- ``bioetl.domain.validation``     — Pure validation functions
- ``bioetl.domain.serialization``  — Centralized JSON helpers
- ``bioetl.domain.composite``      — Composite pipeline models (ADR-026)

Legacy ``bioetl.domain.normalization_*`` modules remain as direct-import
compatibility wrappers only. They are intentionally not exported from the
top-level domain facade; canonical callers should use
``bioetl.domain.normalization``.
"""

from __future__ import annotations

from importlib import import_module as _import_module

_RUNTIME_OBSERVABILITY_PUBLICATION_CONTRACT_MODULE = (
    "bioetl.domain.runtime_observability_publication_contract"
)
_OBSERVABILITY_EVENT_MAPPING_MODULE = "bioetl.domain.observability_event_mapping"

_LAZY_ATTRIBUTE_EXPORTS: dict[str, tuple[str, str]] = {
    "behavior": ("bioetl.domain.behavior", "behavior"),
    "DomainEventObservabilityEnvelope": (
        _OBSERVABILITY_EVENT_MAPPING_MODULE,
        "DomainEventObservabilityEnvelope",
    ),
    "PipelineEvent": ("bioetl.domain.events", "PipelineEvent"),
    "composite": ("bioetl.domain.composite", "composite"),
    "constants": ("bioetl.domain.constants", "constants"),
    "contracts": ("bioetl.domain.contracts", "contracts"),
    "control_plane": ("bioetl.domain.control_plane", "control_plane"),
    "error_types": ("bioetl.domain.error_types", "error_types"),
    "context_cached_bronze": (
        "bioetl.domain.context_cached_bronze",
        "context_cached_bronze",
    ),
    "context_filtering": ("bioetl.domain.context_filtering", "context_filtering"),
    "get_version": ("bioetl.domain.version", "get_version"),
    "lineage": ("bioetl.domain.lineage", "lineage"),
    "observability_contract": (
        "bioetl.domain.observability_contract",
        "observability_contract",
    ),
    "observability_event_mapping": (
        _OBSERVABILITY_EVENT_MAPPING_MODULE,
        "observability_event_mapping",
    ),
    "observability_metric_names": (
        "bioetl.domain.observability_metric_names",
        "observability_metric_names",
    ),
    "pubchem_standardization_catalog": (
        "bioetl.domain.pubchem_standardization_catalog",
        "pubchem_standardization_catalog",
    ),
    "runtime_observability_publication_contract": (
        _RUNTIME_OBSERVABILITY_PUBLICATION_CONTRACT_MODULE,
        "runtime_observability_publication_contract",
    ),
    "get_runtime_observability_publication_contract": (
        _RUNTIME_OBSERVABILITY_PUBLICATION_CONTRACT_MODULE,
        "get_runtime_observability_publication_contract",
    ),
    "is_canonical_runtime_observability_emitter": (
        _RUNTIME_OBSERVABILITY_PUBLICATION_CONTRACT_MODULE,
        "is_canonical_runtime_observability_emitter",
    ),
    "map_domain_event_to_observability_event": (
        _OBSERVABILITY_EVENT_MAPPING_MODULE,
        "map_domain_event_to_observability_event",
    ),
    "types_config_validation": (
        "bioetl.domain.types_config_validation",
        "types_config_validation",
    ),
    "workflow": ("bioetl.domain.workflow", "workflow"),
}

__all__ = [
    "behavior",
    "DomainEventObservabilityEnvelope",
    "PipelineEvent",
    "composite",
    "control_plane",
    "error_types",
    "context_cached_bronze",
    "context_filtering",
    "get_version",
    "get_runtime_observability_publication_contract",
    "is_canonical_runtime_observability_emitter",
    "lineage",
    "map_domain_event_to_observability_event",
    "observability_contract",
    "observability_event_mapping",
    "observability_metric_names",
    "pubchem_standardization_catalog",
    "runtime_observability_publication_contract",
    "types_config_validation",
    "workflow",
    # Data contracts (subpackage)
    "contracts",
    # Constants
    "constants",
]


def __getattr__(name: str) -> object:
    """Resolve public domain facade exports lazily."""
    try:
        module_name, attribute_name = _LAZY_ATTRIBUTE_EXPORTS[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    if name in {
        "behavior",
        "composite",
        "constants",
        "contracts",
        "control_plane",
        "context_cached_bronze",
        "context_filtering",
        "error_types",
        "lineage",
        "observability_contract",
        "observability_event_mapping",
        "observability_metric_names",
        "pubchem_standardization_catalog",
        "runtime_observability_publication_contract",
        "types_config_validation",
        "workflow",
    }:
        value = _import_module(module_name)
    else:
        value = getattr(_import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return stable domain facade exports for introspection."""
    return sorted(set(globals()) | set(__all__))
