"""Domain layer public API with lazy exports.

This package preserves historical ``from bioetl.domain import ...`` usage
without eagerly importing the entire domain tree during package import. The
previous eager facade pulled in large dependency graphs during test collection
and CLI startup, which could stall collection before any test executed.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import bioetl.domain.behavior as behavior
    import bioetl.domain.composite as composite
    import bioetl.domain.constants as constants
    import bioetl.domain.context_cached_bronze as context_cached_bronze
    import bioetl.domain.context_correlation as context_correlation
    import bioetl.domain.context_filtering as context_filtering
    import bioetl.domain.context_run as context_run
    import bioetl.domain.context_time as context_time
    import bioetl.domain.context_validation as context_validation
    import bioetl.domain.contracts as contracts
    import bioetl.domain.control_plane as control_plane
    import bioetl.domain.deterministic_identity as deterministic_identity
    import bioetl.domain.error_types as error_types
    import bioetl.domain.exceptions as exceptions
    import bioetl.domain.lineage as lineage
    import bioetl.domain.observability_contract as observability_contract
    import bioetl.domain.observability_event_mapping as observability_event_mapping
    import bioetl.domain.observability_metric_names as observability_metric_names
    import bioetl.domain.ports as ports
    import bioetl.domain.pubchem_standardization_catalog as pubchem_standardization_catalog
    import bioetl.domain.runtime_observability_publication_contract as runtime_observability_publication_contract
    import bioetl.domain.types as types
    import bioetl.domain.types_config_validation as types_config_validation
    import bioetl.domain.workflow as workflow
    from bioetl.domain.events import PipelineEvent
    from bioetl.domain.observability_event_mapping import (
        DomainEventObservabilityEnvelope,
        map_domain_event_to_observability_event,
    )
    from bioetl.domain.runtime_observability_publication_contract import (
        get_runtime_observability_publication_contract,
        is_canonical_runtime_observability_emitter,
    )
    from bioetl.domain.version import get_version

__all__ = [
    "DomainEventObservabilityEnvelope",
    "PipelineEvent",
    "behavior",
    "composite",
    "constants",
    "context_cached_bronze",
    "context_correlation",
    "context_filtering",
    "context_run",
    "context_time",
    "context_validation",
    "contracts",
    "control_plane",
    "deterministic_identity",
    "error_types",
    "get_runtime_observability_publication_contract",
    "get_version",
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
]

_MODULE_EXPORTS = {
    "behavior": "bioetl.domain.behavior",
    "composite": "bioetl.domain.composite",
    "constants": "bioetl.domain.constants",
    "context_cached_bronze": "bioetl.domain.context_cached_bronze",
    "context_correlation": "bioetl.domain.context_correlation",
    "context_filtering": "bioetl.domain.context_filtering",
    "context_run": "bioetl.domain.context_run",
    "context_time": "bioetl.domain.context_time",
    "context_validation": "bioetl.domain.context_validation",
    "contracts": "bioetl.domain.contracts",
    "control_plane": "bioetl.domain.control_plane",
    "deterministic_identity": "bioetl.domain.deterministic_identity",
    "error_types": "bioetl.domain.error_types",
    "exceptions": "bioetl.domain.exceptions",
    "lineage": "bioetl.domain.lineage",
    "observability_contract": "bioetl.domain.observability_contract",
    "observability_event_mapping": "bioetl.domain.observability_event_mapping",
    "observability_metric_names": "bioetl.domain.observability_metric_names",
    "ports": "bioetl.domain.ports",
    "pubchem_standardization_catalog": "bioetl.domain.pubchem_standardization_catalog",
    "runtime_observability_publication_contract": "bioetl.domain.runtime_observability_publication_contract",
    "types": "bioetl.domain.types",
    "types_config_validation": "bioetl.domain.types_config_validation",
    "workflow": "bioetl.domain.workflow",
}

_ATTRIBUTE_EXPORTS = {
    "DomainEventObservabilityEnvelope": (
        "bioetl.domain.observability_event_mapping",
        "DomainEventObservabilityEnvelope",
    ),
    "PipelineEvent": ("bioetl.domain.events", "PipelineEvent"),
    "get_runtime_observability_publication_contract": (
        "bioetl.domain.runtime_observability_publication_contract",
        "get_runtime_observability_publication_contract",
    ),
    "get_version": ("bioetl.domain.version", "get_version"),
    "is_canonical_runtime_observability_emitter": (
        "bioetl.domain.runtime_observability_publication_contract",
        "is_canonical_runtime_observability_emitter",
    ),
    "map_domain_event_to_observability_event": (
        "bioetl.domain.observability_event_mapping",
        "map_domain_event_to_observability_event",
    ),
}


def __getattr__(name: str) -> object:  # pragma: no cover
    if TYPE_CHECKING:
        raise AttributeError
    module_name = _MODULE_EXPORTS.get(name)
    if module_name is not None:
        value = import_module(module_name)
        globals()[name] = value
        return value

    export = _ATTRIBUTE_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = export
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(
        set(globals()) | set(__all__) | set(_MODULE_EXPORTS) | set(_ATTRIBUTE_EXPORTS)
    )
