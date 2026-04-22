"""Composition services for cross-cutting concerns.

Services in the composition layer coordinate between layers and build
complex objects. Unlike application services, these do not contain
business logic but rather assemble components.

Services:
- MetadataCoordinator: Centralized metadata creation for Medallion layers
- Versioning utilities: code revision provenance, config hash, pipeline version
"""

from __future__ import annotations

from importlib import import_module

from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_code_revision_provenance,
    get_git_commit,
    get_pipeline_version,
)

# Re-export input types from domain.ports for convenience
from bioetl.domain.ports import (
    BronzeMetadataInput,
    GoldMetadataInput,
    SilverMetadataInput,
)

_LAZY_EXPORT_MODULES: dict[str, str] = {
    "MetadataCoordinator": "bioetl.composition._services",
}

__all__ = [
    "BronzeMetadataInput",
    "GoldMetadataInput",
    "MetadataCoordinator",
    "SilverMetadataInput",
    "compute_config_hash",
    "get_code_revision_provenance",
    "get_git_commit",
    "get_pipeline_version",
]


def __getattr__(name: str) -> object:
    """Resolve compatibility exports lazily to avoid bootstrap import cycles."""
    try:
        module_name = _LAZY_EXPORT_MODULES[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy re-exports for help() and shell introspection."""
    return sorted(set(globals()) | set(__all__))
