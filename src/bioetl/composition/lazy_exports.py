"""Public lazy-export helper facade for composition package consumers."""

from __future__ import annotations

from bioetl.composition._lazy_exports import (
    build_lazy_export_hooks,
    install_cached_public_exports,
    install_lazy_exports,
    lazy_export_dir,
    resolve_lazy_export,
)

__all__ = [
    "build_lazy_export_hooks",
    "install_cached_public_exports",
    "install_lazy_exports",
    "lazy_export_dir",
    "resolve_lazy_export",
]
