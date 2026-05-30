"""Shared lazy-export helpers for composition wiring facades."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


def resolve_lazy_export(
    *,
    module_name: str,
    public_exports: Mapping[str, tuple[str, str]],
    name: str,
    namespace: dict[str, object],
) -> object:
    """Resolve one lazily exported symbol for a wiring facade module."""
    export = public_exports.get(name)
    if export is None:
        raise AttributeError(f"module {module_name!r} has no attribute {name!r}")
    target_module_name, attr_name = export
    value = getattr(import_module(target_module_name), attr_name)
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
    public_exports: Mapping[str, tuple[str, str]],
) -> None:
    """Install lazy export hooks for one wiring facade module."""
    export_names = list(public_exports)
    namespace["__all__"] = export_names

    def __getattr__(name: str) -> object:
        return resolve_lazy_export(
            module_name=module_name,
            public_exports=public_exports,
            name=name,
            namespace=namespace,
        )

    def __dir__() -> list[str]:
        return lazy_export_dir(namespace, export_names)

    namespace["__getattr__"] = __getattr__
    namespace["__dir__"] = __dir__
