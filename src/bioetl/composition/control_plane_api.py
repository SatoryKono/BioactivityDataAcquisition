"""Public control-plane composition API."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "get_adr_service",
    "get_config_service",
    "get_export_service",
    "get_lineage_service",
    "get_lock_service",
    "get_run_manifest_service",
]

_SERVICES_MODULE = "bioetl.composition._services"

get_adr_service: object
get_config_service: object
get_export_service: object
get_lineage_service: object
get_lock_service: object
get_run_manifest_service: object


def __getattr__(name: str) -> object:
    """Resolve control-plane exports lazily to avoid CLI import fan-out."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(_SERVICES_MODULE), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
