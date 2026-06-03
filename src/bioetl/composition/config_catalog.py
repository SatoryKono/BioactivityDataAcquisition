"""Lightweight config catalog helpers for administrative read-only commands."""

from __future__ import annotations

from pathlib import Path

__all__ = ["list_configured_pipeline_names"]

from bioetl.composition.composite_api import list_configured_pipeline_names as _impl


def list_configured_pipeline_names(*, configs_root: Path | None = None) -> list[str]:
    """Return configured entity pipeline names without runtime registration."""
    return _impl(configs_root=configs_root)
