"""Lazy export helpers for control-plane compatibility facades."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.application.core.wiring._lazy_export_facade import (
    install_lazy_export_facade as _install_lazy_export_facade,
)


def install_lazy_export_facade(
    namespace: dict[str, object],
    module_name: str,
    public_exports: Mapping[str, tuple[str, str]],
) -> None:
    """Install lazy export hooks for one control-plane facade module."""
    _install_lazy_export_facade(namespace, module_name, public_exports)


__all__ = ["install_lazy_export_facade"]
