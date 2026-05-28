"""Public seam for control-plane manifest helper functions."""

from __future__ import annotations

from importlib import import_module

_PRIVATE_MODULE = "bioetl.composition.runtime_builders._run_manifest_support"
__all__ = list(import_module(_PRIVATE_MODULE).__all__)


def __getattr__(name: str) -> object:
    """Resolve public helper exports lazily from the private owner module."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(_PRIVATE_MODULE), name)


def __dir__() -> list[str]:
    """Expose lazy helper exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
