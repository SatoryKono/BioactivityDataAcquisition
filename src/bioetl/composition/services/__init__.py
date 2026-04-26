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

_DOMAIN_PORTS_MODULE = "bioetl.domain.ports"

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "BronzeMetadataInput": (_DOMAIN_PORTS_MODULE, "BronzeMetadataInput"),
    "GoldMetadataInput": (_DOMAIN_PORTS_MODULE, "GoldMetadataInput"),
    "MetadataCoordinator": ("bioetl.composition._services", "MetadataCoordinator"),
    "SilverMetadataInput": (_DOMAIN_PORTS_MODULE, "SilverMetadataInput"),
}

__all__ = [
    *_LAZY_EXPORTS,
    "compute_config_hash",
    "get_code_revision_provenance",
    "get_git_commit",
    "get_pipeline_version",
]


def __getattr__(name: str) -> object:
    """Resolve compatibility exports lazily to avoid bootstrap import cycles."""
    try:
        module_name, attr_name = _LAZY_EXPORTS[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy re-exports for help() and shell introspection."""
    return sorted(set(globals()) | set(__all__))
