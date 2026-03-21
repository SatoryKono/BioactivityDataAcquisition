"""Helpers for compatibility shims in the CLI commands layer."""

from __future__ import annotations

import sys
from importlib import import_module


def alias_module(module_name: str, target_module_name: str) -> None:
    """Replace a compat shim module with the canonical target module object."""
    target_module = import_module(target_module_name)
    current_module = sys.modules[module_name]
    current_module.__dict__.update(
        {
            name: getattr(target_module, name)
            for name in dir(target_module)
            if not name.startswith("__")
        }
    )
    current_module.__dict__["__doc__"] = getattr(target_module, "__doc__", None)
    current_module.__dict__["__all__"] = getattr(
        target_module,
        "__all__",
        [name for name in dir(target_module) if not name.startswith("_")],
    )
    sys.modules[module_name] = target_module


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
