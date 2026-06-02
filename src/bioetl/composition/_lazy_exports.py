"""Shared helpers for composition lazy public export facades."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from importlib import import_module


def resolve_lazy_export(
    *,
    module_globals: dict[str, object],
    public_exports: Mapping[str, str],
    module_name: str,
    name: str,
    cache: bool = False,
) -> object:
    """Resolve a lazy public export and optionally cache it in module globals."""
    target_module = public_exports.get(name)
    if target_module is None:
        raise AttributeError(f"module {module_name!r} has no attribute {name!r}")

    value = getattr(import_module(target_module), name)
    if cache:
        module_globals[name] = value
    return value


def lazy_export_dir(
    *,
    module_globals: Mapping[str, object],
    public_exports: Mapping[str, str],
    explicit_exports: Iterable[str],
) -> list[str]:
    """Return stable introspection results for lazy-export modules."""
    return sorted(set(module_globals) | set(public_exports) | set(explicit_exports))
