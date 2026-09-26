"""Lazy export helpers for application-core compatibility facades."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.application.core.wiring.lazy_export_hooks import (
    install_lazy_export_facade as _install_lazy_export_facade,
)


def install_lazy_export_facade(
    namespace: dict[str, object],
    module_name: str,
    public_exports: Mapping[str, tuple[str, str]],
) -> None:
    """Install lazy export hooks for one application-core facade module."""
    _install_lazy_export_facade(namespace, module_name, public_exports)


__all__ = ["install_lazy_export_facade"]
