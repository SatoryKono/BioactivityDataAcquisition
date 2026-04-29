"""Helpers for compatibility shims in the CLI commands layer."""

from __future__ import annotations

import sys
from importlib import import_module


def alias_module(module_name: str, target_module_name: str) -> None:
    """Replace a retained public command seam with its canonical target module.

    This is reserved for command modules that are documented public patch/import
    seams. Support-only helpers should live under their canonical owner modules
    rather than adding top-level compatibility shims.
    """
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
