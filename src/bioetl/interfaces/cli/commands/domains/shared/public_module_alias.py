"""Helpers for thin internal wrappers over retained public CLI modules."""

from __future__ import annotations

from importlib import import_module


def install_public_module_alias(
    module_globals: dict[str, object],
    *,
    public_module: str,
    exported_names: tuple[str, ...],
) -> None:
    """Bind exported names from one public module into a thin wrapper module."""
    public = import_module(public_module)
    for name in exported_names:
        module_globals[name] = getattr(public, name)
    module_globals["__all__"] = list(exported_names)
