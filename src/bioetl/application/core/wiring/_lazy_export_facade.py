"""Shared lazy-export helpers for composition wiring facades."""
from __future__ import annotations

from collections.abc import Mapping
from importlib import import_module

type LazyExportTarget = str | tuple[str, str]

def _resolve_export_target(
    target: LazyExportTarget,
    export_name: str,
) -> tuple[str, str]:
    return target if isinstance(target, tuple) else (target, export_name)

def resolve_lazy_export(
    *,
    module_name: str,
    public_exports: Mapping[str, LazyExportTarget],
    name: str,
    namespace: dict[str, object],
) -> object:
    """Resolve one lazily exported symbol for a wiring facade module."""
    target = public_exports.get(name)
    if target is None:
        raise AttributeError(f"module {module_name!r} has no attribute {name!r}")
    target_module, target_attr = _resolve_export_target(target, name)
    value = getattr(import_module(target_module), target_attr)
    namespace[name] = value
    return value

def lazy_export_dir(
    namespace: dict[str, object],
    export_names: list[str],
) -> list[str]:
    """Return directory entries for one lazy wiring facade."""
    return sorted(set(namespace) | set(export_names))

def install_lazy_export_facade(
    namespace: dict[str, object],
    module_name: str,
    public_exports: Mapping[str, LazyExportTarget],
) -> None:
    """Install lazy export hooks for one wiring facade module."""
    export_names = list(public_exports)
    namespace["__all__"] = export_names
    def _module_getattr(name: str) -> object:
        return resolve_lazy_export(
            module_name=module_name,
            public_exports=public_exports,
            name=name,
            namespace=namespace,
        )
    def _module_dir() -> list[str]:
        return lazy_export_dir(namespace, export_names)

    namespace["__getattr__"] = _module_getattr
    namespace["__dir__"] = _module_dir
