"""Lazy export helpers for control-plane compatibility facades."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


def install_lazy_export_facade(
    namespace: dict[str, object],
    module_name: str,
    public_exports: Mapping[str, tuple[str, str]],
) -> None:
    """Install lazy export hooks for one control-plane facade module."""
    export_names = list(public_exports)
    namespace["__all__"] = export_names

    def __getattr__(name: str) -> object:
        try:
            target_module_name, attr_name = public_exports[name]
        except KeyError as exc:  # pragma: no cover - standard attribute path
            raise AttributeError(
                f"module {module_name!r} has no attribute {name!r}"
            ) from exc
        value = getattr(import_module(target_module_name), attr_name)
        namespace[name] = value
        return value

    def __dir__() -> list[str]:
        return sorted(set(namespace) | set(export_names))

    namespace["__getattr__"] = __getattr__
    namespace["__dir__"] = __dir__


__all__ = ["install_lazy_export_facade"]
