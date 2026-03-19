"""Helpers for compatibility re-export shims in the CLI commands layer."""

from __future__ import annotations

from importlib import import_module
import sys


def reexport_module(module_name: str, target_module_name: str) -> None:
    """Populate a shim module with the public and private names of a target module."""
    target_module = import_module(target_module_name)
    target_globals = sys.modules[module_name].__dict__
    exported_names = {
        name: getattr(target_module, name)
        for name in dir(target_module)
        if not name.startswith("__")
    }
    target_globals.update(exported_names)
    target_globals["__doc__"] = getattr(target_module, "__doc__", None)
    target_globals["__all__"] = getattr(
        target_module,
        "__all__",
        [name for name in exported_names if not name.startswith("_")],
    )
